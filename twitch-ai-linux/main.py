#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitch AI Voice Bot для Linux — 24/7, не отваливается после 5 мин тишины
Groq (gsk_...) + pyttsx3 (голос из системы) + TwitchIO
Полный доступ к компу опционально через allow_exec

Установка на Linux:
  sudo apt install espeak espeak-data libespeak1 ffmpeg -y
  pip install -r requirements.txt
  cp config.json.example config.json
  nano config.json (вставь канал и gsk_ ключ)
  python3 main.py

24/7 через systemd:
  sudo cp twitch-ai.service /etc/systemd/system/
  sudo systemctl enable --now twitch-ai
"""

import asyncio
import json
import os
import sys
import time
import subprocess
import traceback
from pathlib import Path

import pyttsx3
from twitchio.ext import commands
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        print(f"❌ Нет {CONFIG_PATH}, скопируй config.json.example -> config.json и заполни!")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # env override
    cfg["twitch_channel"] = os.getenv("TWITCH_CHANNEL") or cfg.get("twitch_channel")
    cfg["twitch_token"] = os.getenv("TWITCH_TOKEN") or cfg.get("twitch_token")
    cfg["groq_api_key"] = os.getenv("GROQ_API_KEY") or cfg.get("groq_api_key")
    return cfg

CONFIG = load_config()

# TTS setup — работает на Linux через espeak, без интернета
print("🔊 Инициализирую голос (pyttsx3 + espeak)...")
engine = pyttsx3.init()
# Настройка голоса
voices = engine.getProperty('voices')
print(f"Найдено голосов: {len(voices)}")
for i, v in enumerate(voices):
    print(f"  [{i}] {v.name} - {v.languages} - {v.id}")
    if "ru" in str(v.languages).lower() or "russian" in v.name.lower():
        print(f"    → русский голос найден!")

# Выбираем голос
if CONFIG.get("voice_id") is not None and CONFIG["voice_id"] < len(voices):
    engine.setProperty('voice', voices[CONFIG["voice_id"]].id)
else:
    # пробуем найти русский
    for v in voices:
        if "ru" in str(v.languages).lower() or "russian" in v.name.lower() or "ru" in v.id.lower():
            engine.setProperty('voice', v.id)
            print(f"✅ Выбран русский голос: {v.name}")
            break

engine.setProperty('rate', CONFIG.get("voice_rate", 180))
engine.setProperty('volume', CONFIG.get("voice_volume", 0.9))

# Очередь голоса — чтобы не перебивал
voice_queue = asyncio.Queue()
is_speaking = False

async def speaker_worker():
    global is_speaking
    while True:
        text = await voice_queue.get()
        is_speaking = True
        try:
            print(f"🔊 Говорю: {text[:80]}...")
            # pyttsx3 блокирующий, запускаем в thread
            await asyncio.to_thread(speak_blocking, text)
        except Exception as e:
            print(f"TTS ошибка: {e}")
        is_speaking = False
        voice_queue.task_done()

def speak_blocking(text):
    engine.say(text)
    engine.runAndWait()

def speak_async(text):
    # Добавить в очередь
    try:
        voice_queue.put_nowait(text)
    except asyncio.QueueFull:
        pass
    # Для синхронного вызова из вне event loop
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(voice_queue.put(text))
    except RuntimeError:
        # нет loop, говорим напрямую
        engine.say(text)
        engine.runAndWait()

# Groq client
groq_client = Groq(api_key=CONFIG["groq_api_key"])
print(f"✅ Groq клиент готов, модель {CONFIG.get('groq_model','llama-3.3-70b-versatile')}")

async def ask_groq(user_msg: str, username: str) -> str:
    model = CONFIG.get("groq_model", "llama-3.3-70b-versatile")
    bot_name = CONFIG.get("bot_name", "AI")
    personality = CONFIG.get("personality", "Ты веселый AI.")
    system_prompt = f"{personality}\n\nТы бот {bot_name} на твич канале {CONFIG['twitch_channel']}. Отвечай коротко, 1-2 предложения, на русском. Пользователь чата: {username}."
    try:
        print(f"[GROQ] → {username}: {user_msg[:60]}")
        # Groq sync, запускаем в thread чтобы не блочить
        def _call():
            return groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.8,
                max_tokens=150,
                top_p=0.9
            )
        resp = await asyncio.to_thread(_call)
        answer = resp.choices[0].message.content.strip()
        print(f"[GROQ] ← {answer[:80]}... tokens={resp.usage.total_tokens if resp.usage else '?'}")
        return answer
    except Exception as e:
        err = str(e)
        print(f"[GROQ] ❌ {err}")
        if "credits" in err.lower() or "limit" in err.lower() or "quota" in err.lower() or "429" in err:
            msg = "У меня кончились кредиты на сегодня, хозяин скоро сменит ключ!"
            speak_async(msg)
            return msg
        return None

# Twitch bot — 24/7, не отваливается
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=CONFIG["twitch_token"],
            prefix="!",
            initial_channels=[CONFIG["twitch_channel"]],
            # Важно: reconnect, keepalive
            heartbeat=30.0
        )
        self.msg_count = 0
        self.ai_count = 0

    async def event_ready(self):
        print(f"✅ Подключен как {self.nick} к #{CONFIG['twitch_channel']} — слушаю 24/7, не отключусь!")
        speak_async(f"Подключен к чату канала {CONFIG['twitch_channel']}. Слушаю 24 на 7 на линуксе!")
        # Keepalive лог каждые 60 сек
        self.loop.create_task(self.keepalive_task())

    async def keepalive_task(self):
        while True:
            await asyncio.sleep(60)
            print(f"💓 Keepalive — всё ещё слушаю #{CONFIG['twitch_channel']} | сообщений: {self.msg_count} | ответов: {self.ai_count} | uptime {int(time.time() - start_time)}с")
            # Если вдруг отвалился — TwitchIO сам реконнектит, но на всякий
            if not self.connected_channels:
                print("⚠️ Нет подключенных каналов, пробую переподключиться...")
                try:
                    await self.join_channels([CONFIG["twitch_channel"]])
                except Exception as e:
                    print(f"Reconnect fail: {e}")

    async def event_message(self, message):
        if message.echo:
            return
        self.msg_count += 1
        username = message.author.display_name or message.author.name
        content = message.content
        print(f"[CHAT] {username}: {content}")

        # Фильтры
        bot_name = CONFIG.get("bot_name","AI").lower()
        mention_only = CONFIG.get("mention_only", False)
        reply_all = CONFIG.get("reply_all", True)

        if mention_only and bot_name not in content.lower() and "@" not in content:
            print(f"[SKIP] mention_only, нет упоминания")
            return
        if content.startswith("!") and not content.startswith(CONFIG.get("exec_prefix","!exec")):
            # команды твича игнорим
            return

        # Проверка exec
        if CONFIG.get("allow_exec") and content.startswith(CONFIG.get("exec_prefix","!exec")):
            cmd = content[len(CONFIG.get("exec_prefix","!exec")):].strip()
            if cmd:
                print(f"[EXEC] {username} хочет выполнить: {cmd}")
                try:
                    result = await asyncio.to_thread(subprocess.run, cmd, shell=True, capture_output=True, text=True, timeout=10)
                    out = (result.stdout + result.stderr)[:500]
                    await message.channel.send(f"✅ {username} выполнил: {out[:200]}")
                    speak_async(f"Выполнил команду {cmd}")
                except Exception as e:
                    await message.channel.send(f"❌ Ошибка: {e}")
                return

        # Спрашиваем Groq
        answer = await ask_groq(content, username)
        if answer:
            self.ai_count += 1
            # Только говорить, не писать в чат (по желанию юзера)
            if CONFIG.get("write_to_chat", False):
                try:
                    await message.channel.send(f"{answer}")
                except Exception as e:
                    print(f"Не смог отправить в чат: {e}")
            else:
                print(f"[NO CHAT WRITE] Только голос + оверлей, в чат не пишу (write_to_chat=false)")
            
            # Обновить оверлей для OBS
            if CONFIG.get("show_overlay", True):
                try:
                    update_overlay(username, content, answer)
                except Exception as e:
                    print(f"Overlay error: {e}")
            
            speak_async(answer)

    async def event_command_error(self, ctx, error):
        print(f"Command error: {error}")

start_time = time.time()
latest_overlay = {"user": "", "question": "", "answer": "", "time": ""}

def update_overlay(user, question, answer):
    global latest_overlay
    latest_overlay = {
        "user": user,
        "question": question,
        "answer": answer,
        "time": time.strftime("%H:%M:%S")
    }
    # Сохраняем в файл для оверлея
    try:
        overlay_path = Path(__file__).parent / "overlay_data.json"
        with open(overlay_path, "w", encoding="utf-8") as f:
            json.dump(latest_overlay, f, ensure_ascii=False)
    except Exception as e:
        print(f"Overlay save fail: {e}")

async def overlay_server():
    """HTTP сервер для OBS оверлея — показывает текст на стриме"""
    from aiohttp import web
    import pathlib
    
    async def handle_overlay(request):
        html_path = pathlib.Path(__file__).parent / "overlay.html"
        if not html_path.exists():
            return web.Response(text="overlay.html не найден", status=404)
        return web.FileResponse(html_path)
    
    async def handle_data(request):
        return web.json_response(latest_overlay)
    
    async def handle_root(request):
        return web.Response(text=f"Twitch AI Overlay running. OBS Browser Source: http://localhost:{CONFIG.get('overlay_port',8080)}/overlay.html | Data: /api/data", content_type="text/plain")
    
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/overlay.html', handle_overlay)
    app.router.add_get('/api/data', handle_data)
    app.router.add_get('/overlay_data.json', handle_data)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = CONFIG.get("overlay_port", 8080)
    site = web.TCPSite(runner, '0.0.0.0', port)
    try:
        await site.start()
        print(f"🖥️ Оверлей для OBS запущен: http://localhost:{port}/overlay.html")
        print(f"   Добавь в OBS как Browser Source → URL: http://localhost:{port}/overlay.html")
        print(f"   Размер: 800x200, прозрачный фон")
    except Exception as e:
        print(f"Overlay server fail (порт {port} занят?): {e}")

    # Keep running
    while True:
        await asyncio.sleep(3600)

async def main():
    # Проверка конфига
    if not CONFIG.get("twitch_channel") or CONFIG["twitch_channel"] == "твой_канал_без_решетки":
        print("❌ Вставь twitch_channel в config.json")
        return
    if not CONFIG.get("twitch_token") or "oauth" not in CONFIG.get("twitch_token",""):
        print("❌ Вставь twitch_token в config.json — бери на https://twitchtokengenerator.com (выбери Bot Chat Token)")
        return
    if not CONFIG.get("groq_api_key") or not CONFIG["groq_api_key"].startswith("gsk_"):
        print("❌ Вставь groq_api_key gsk_... в config.json — бери на https://console.groq.com/keys")
        return

    # Запускаем speaker worker
    asyncio.create_task(speaker_worker())
    
    # Запускаем оверлей сервер для OBS если включен
    if CONFIG.get("show_overlay", True):
        asyncio.create_task(overlay_server())

    bot = Bot()
    # Бесконечный цикл с реконнектом — 24/7
    while True:
        try:
            print("🚀 Запускаю бота... (24/7 режим, не отключится после 5 мин тишины)")
            await bot.start()
        except Exception as e:
            print(f"❌ Бот упал: {e}\n{traceback.format_exc()}")
            print("🔁 Перезапуск через 5 сек...")
            await asyncio.sleep(5)
            # Перезагружаем конфиг на случай смены ключа
            global CONFIG
            try:
                CONFIG = load_config()
            except:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Остановлен пользователем")
        engine.stop()
