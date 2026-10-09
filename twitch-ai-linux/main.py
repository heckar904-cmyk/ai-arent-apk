#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitch AI Voice Bot v3 — РЕАЛЬНЫЙ контроль Linux
- Читает чат, НЕ пишет в чат, только голос + оверлей на стриме
- Реально управляет Linux: команды, скрин экрана, мышка, файлы, установка приложений (с разрешением)
- Понимает кто главный в чате (broadcaster)
- Память в memory.jsonl — помнит вчера/позавчера даже после переустановки
- Мысли в thoughts.txt
- Характеристики системы для проверки нагрузки
- Правила: no 18+, no пропаганда, no 112 (шутит), no вирусы
- Если ключ истек — на экране "Модель недоступна, владелец поменяет"
"""

import asyncio
import json
import os
import sys
import time
import subprocess
import traceback
import re
import base64
from pathlib import Path
from datetime import datetime

import pyttsx3
from twitchio.ext import commands
from groq import Groq
from dotenv import load_dotenv

# Опциональные зависимости для реального контроля
try:
    import mss
    from PIL import Image
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.json"
MEMORY_PATH = Path(__file__).parent / "memory.jsonl"
THOUGHT_PATH = Path(__file__).parent / "thoughts.txt"
SYSTEM_INFO_PATH = Path(__file__).parent / "system_info.json"
OVERLAY_DATA_PATH = Path(__file__).parent / "overlay_data.json"

def load_config():
    if not CONFIG_PATH.exists():
        print(f"❌ Нет {CONFIG_PATH}, скопируй config.json.example -> config.json")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # env override
    cfg["twitch_channel"] = os.getenv("TWITCH_CHANNEL") or cfg.get("twitch_channel")
    cfg["twitch_token"] = os.getenv("TWITCH_TOKEN") or cfg.get("twitch_token")
    cfg["groq_api_key"] = os.getenv("GROQ_API_KEY") or cfg.get("groq_api_key")
    return cfg

CONFIG = load_config()

# === СИСТЕМНЫЕ ХАРАКТЕРИСТИКИ ===
def collect_system_info():
    info = {
        "time": datetime.now().isoformat(),
        "os": os.uname()._asdict() if hasattr(os, 'uname') else str(os.name),
        "cpu_count": os.cpu_count(),
    }
    if HAS_PSUTIL:
        info["ram_total_mb"] = psutil.virtual_memory().total // 1024 // 1024
        info["ram_available_mb"] = psutil.virtual_memory().available // 1024 // 1024
        info["disk_free_gb"] = psutil.disk_usage("/").free // 1024 // 1024 // 1024
        info["cpu_percent"] = psutil.cpu_percent(interval=1)
    else:
        info["ram_total_mb"] = 0
        info["ram_available_mb"] = 0
    # Сохраняем
    try:
        with open(SYSTEM_INFO_PATH, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    except:
        pass
    print(f"🖥️ Система: CPU {info.get('cpu_count')} | RAM {info.get('ram_available_mb')}MB free | Disk {info.get('disk_free_gb')}GB free")
    return info

SYSTEM_INFO = collect_system_info()

# === ПАМЯТЬ — помнит вчера/позавчера ===
def write_memory(user, question, answer, thought="", action=""):
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "datetime": datetime.now().isoformat(),
        "user": user,
        "question": question,
        "answer": answer,
        "thought": thought,
        "action": action,
        "channel": CONFIG.get("twitch_channel")
    }
    try:
        with open(MEMORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Memory write fail: {e}")

def read_recent_memory(n=20):
    if not MEMORY_PATH.exists():
        return []
    try:
        lines = MEMORY_PATH.read_text(encoding="utf-8").strip().split("\n")
        # Последние n
        recent = []
        for line in lines[-n:]:
            try:
                recent.append(json.loads(line))
            except:
                continue
        return recent
    except:
        return []

def write_thought(thought):
    try:
        with open(THOUGHT_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {thought}\n")
    except:
        pass

# === TTS ===
print("🔊 Инициализирую голос...")
engine = pyttsx3.init()
voices = engine.getProperty('voices')
for v in voices:
    if "ru" in str(v.languages).lower() or "russian" in v.name.lower():
        engine.setProperty('voice', v.id)
        print(f"✅ Русский голос: {v.name}")
        break
engine.setProperty('rate', CONFIG.get("voice_rate", 180))
engine.setProperty('volume', CONFIG.get("voice_volume", 0.9))

voice_queue = asyncio.Queue()

async def speaker_worker():
    while True:
        text = await voice_queue.get()
        try:
            await asyncio.to_thread(lambda: (engine.say(text), engine.runAndWait()))
        except Exception as e:
            print(f"TTS fail: {e}")
        voice_queue.task_done()

def speak_async(text):
    try:
        # Убираем кодовые блоки для голоса
        clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        clean = re.sub(r'\[EXEC:.*?\]', '', clean)
        clean = clean.strip()
        if clean:
            asyncio.create_task(voice_queue.put(clean))
    except RuntimeError:
        engine.say(text)
        engine.runAndWait()

# === GROQ ===
groq_client = Groq(api_key=CONFIG["groq_api_key"])
print(f"✅ Groq готов: {CONFIG.get('groq_model')} + vision {CONFIG.get('groq_vision_model')}")

# Флаг истекшего ключа
KEY_EXPIRED = False
OVERLAY_MESSAGE = ""

def set_key_expired():
    global KEY_EXPIRED, OVERLAY_MESSAGE
    KEY_EXPIRED = True
    OVERLAY_MESSAGE = "⚠️ Модель недоступна — истек ключ Groq, владелец скоро поменяет, чат заработает"
    update_overlay("Система", "Ключ истек", OVERLAY_MESSAGE)
    print(OVERLAY_MESSAGE)

# === РЕАЛЬНЫЙ КОНТРОЛЬ LINUX ===
def exec_command(cmd, need_sudo=False, sudo_password=None):
    """Реально выполняет команду на Linux"""
    print(f"[EXEC] {cmd} (sudo={need_sudo})")
    write_thought(f"Хочу выполнить команду: {cmd}, sudo={need_sudo}")
    try:
        if need_sudo and sudo_password:
            # Выполнить с sudo
            proc = subprocess.run(
                f"echo '{sudo_password}' | sudo -S {cmd}",
                shell=True, capture_output=True, text=True, timeout=30
            )
        else:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = (proc.stdout + proc.stderr)[:2000]
        print(f"[EXEC RESULT] {out[:200]}...")
        write_thought(f"Команда {cmd} выполнена, результат: {out[:200]}")
        return out, proc.returncode
    except subprocess.TimeoutExpired:
        return "Команда зависла, убита по таймауту 30с", 1
    except Exception as e:
        return f"Ошибка выполнения: {e}", 1

def take_screenshot():
    """Делает скрин экрана — чтобы AI видел что на экране"""
    if not HAS_MSS:
        return None, "mss не установлен, поставь pip install mss Pillow"
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            # Сохраняем
            path = Path(__file__).parent / "last_screenshot.png"
            mss.tools.to_png(img.rgb, img.size, output=str(path))
            print(f"📸 Скрин сохранен: {path} {img.size}")
            return str(path), f"Скрин {img.size} сохранен"
    except Exception as e:
        return None, f"Скрин fail: {e}"

def open_yandex_browser(query=None):
    """Открывает Яндекс Браузер и ищет"""
    # Проверяем что установлено
    browsers = ["yandex-browser", "yandex_browser", "yandex", "firefox", "chromium", "google-chrome"]
    found = None
    for b in browsers:
        if subprocess.run(f"which {b}", shell=True, capture_output=True).returncode == 0:
            found = b
            break
    if not found:
        return "Яндекс Браузер не установлен, пробую xdg-open"
    
    try:
        if query:
            url = f"https://yandex.ru/search/?text={query}"
            if "yandex" in found:
                subprocess.Popen([found, url])
            else:
                subprocess.Popen(["xdg-open", url])
            return f"Открыл {found} с запросом: {query}"
        else:
            subprocess.Popen([found])
            return f"Открыл {found}"
    except Exception as e:
        return f"Не смог открыть браузер: {e}"

def check_if_safe_to_install(app_name):
    """Проверяет характеристики перед установкой — не нагрузит ли комп"""
    if not HAS_PSUTIL:
        return True, "psutil нет, не могу проверить, но разрешаю"
    
    ram_avail = psutil.virtual_memory().available // 1024 // 1024
    disk_free = psutil.disk_usage("/").free // 1024 // 1024 // 1024
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Тяжелые приложения
    heavy_apps = ["chrome", "firefox", "blender", "gimp", "steam", "docker"]
    is_heavy = any(h in app_name.lower() for h in heavy_apps)
    
    if is_heavy and ram_avail < CONFIG.get("max_ram_for_install_mb", 500):
        return False, f"Мало RAM: {ram_avail}MB свободно, для {app_name} нужно больше, не буду нагружать комп"
    if disk_free < 2:
        return False, f"Мало диска: {disk_free}GB свободно, не буду ставить {app_name}"
    if cpu_percent > 85:
        return False, f"CPU загружен {cpu_percent}%, подожду с установкой {app_name}"
    
    return True, f"Можно ставить {app_name}: RAM {ram_avail}MB free, Disk {disk_free}GB free, CPU {cpu_percent}%"

def is_owner(username, badges):
    """Проверяет главный ли в чате — broadcaster"""
    channel = CONFIG.get("twitch_channel","").lower()
    owner_name = CONFIG.get("owner_username","").lower()
    
    if username.lower() == channel:
        return True
    if owner_name and username.lower() == owner_name:
        return True
    if badges and "broadcaster" in str(badges).lower():
        return True
    return False

# === ПРАВИЛА — что нельзя ===
BLOCKED_KEYWORDS = ["порно", "18+", "xxx", "пропаганда", "наци", "вирус", "троян", "майнер"]
DANGEROUS_COMMANDS = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "shutdown -h now", "reboot"]

def check_rules(text):
    """Проверяет правила — нельзя 18+, пропаганда, вирусы, 112"""
    lower = text.lower()
    
    # 112 — шутит
    if "112" in text or "позвони в 112" in lower or "вызови полицию" in lower or "вызови скорую" in lower:
        return False, "ха-ха-ха, как же я тебе поверил! Я не звоню в 112, это не игрушки"
    
    # 18+
    for kw in BLOCKED_KEYWORDS:
        if kw in lower:
            return False, f"Не могу — тема {kw} запрещена в правилах"
    
    # Опасные команды
    for dc in DANGEROUS_COMMANDS:
        if dc in lower:
            return False, f"Опасная команда {dc} запрещена"
    
    # Вирус/нагрузка
    if "скачай" in lower and ("вирус" in lower or "троян" in lower or "майнер" in lower):
        return False, "Не качаю вирусы и майнеры — это нагрузит комп и запрещено"
    
    return True, "ok"

# === OVERLAY ===
latest_overlay = {"user": "", "question": "", "answer": "", "time": ""}

def update_overlay(user, question, answer):
    global latest_overlay, OVERLAY_MESSAGE
    if KEY_EXPIRED:
        answer = OVERLAY_MESSAGE
    latest_overlay = {
        "user": user,
        "question": question,
        "answer": answer,
        "time": datetime.now().strftime("%H:%M:%S"),
        "key_expired": KEY_EXPIRED
    }
    try:
        with open(OVERLAY_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(latest_overlay, f, ensure_ascii=False)
    except:
        pass

async def overlay_server():
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
        return web.Response(text=f"Overlay: http://localhost:{CONFIG.get('overlay_port',8080)}/overlay.html", content_type="text/plain")
    
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/overlay.html', handle_overlay)
    app.router.add_get('/api/data', handle_data)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = CONFIG.get("overlay_port", 8080)
    site = web.TCPSite(runner, '0.0.0.0', port)
    try:
        await site.start()
        print(f"🖥️ Оверлей для OBS: http://localhost:{port}/overlay.html")
    except Exception as e:
        print(f"Overlay fail: {e}")
    while True:
        await asyncio.sleep(3600)

async def ask_groq_with_memory(user_msg: str, username: str, is_owner_flag: bool):
    global KEY_EXPIRED
    if KEY_EXPIRED:
        return "Модель недоступна — истек ключ Groq, владелец скоро поменяет, чат заработает"
    
    # Проверка правил
    ok, rule_msg = check_rules(user_msg)
    if not ok:
        write_thought(f"Сообщение {username}: {user_msg} — заблокировано правилами: {rule_msg}")
        return rule_msg
    
    # Память — последние 10 сообщений
    recent = read_recent_memory(10)
    memory_context = ""
    if recent:
        memory_context = "Вот что было раньше (память):\n"
        for m in recent[-5:]:
            memory_context += f"{m['date']} {m['user']}: {m['question']} -> {m['answer'][:80]}\n"
    
    # Системная инфа
    sys_info = f"Система: CPU {SYSTEM_INFO.get('cpu_count')} cores, RAM free {SYSTEM_INFO.get('ram_available_mb')}MB, Disk free {SYSTEM_INFO.get('disk_free_gb')}GB, OS {SYSTEM_INFO.get('os')}"
    
    # Роль владельца
    owner_info = f"Пишет {'ВЛАДЕЛЕЦ канала' if is_owner_flag else 'зритель'} {username}. "
    if CONFIG.get("owner_sleeping"):
        owner_info += "Владелец сейчас спит, не контролирует комп. "
    
    # Правила для AI
    rules = """
Правила:
- Ты реально управляешь Linux, можешь выполнять команды, смотреть экран, открывать браузер
- Если просят установить приложение — проверь характеристики, спроси разрешение если опасное, если владелец спит — скажи "Не могу установить, владелец ушел спать и не контролирует меня"
- Если просят открыть Яндекс Браузер и найти — открывай: [EXEC: yandex-browser https://yandex.ru/search/?text=запрос]
- Если просят выключить комп — скажи "Хорошо, выключил" но реально выключай только если владелец разрешил (is_owner)
- Если просят скачать что-то — спроси разрешение, проверь не вирус ли, не нагрузит ли комп
- Если просят позвонить в 112 — шути "ха-ха-ха, как же я тебе поверил"
- Если 18+, пропаганда, вирус — отказывай
- Отвечай коротко 1-2 предложения на русском
- Если хочешь выполнить команду, пиши в формате [EXEC: команда]
- Если хочешь скрин экрана, пиши [SCREEN]
- Если хочешь открыть браузер, пиши [BROWSER: запрос]
"""
    
    personality = CONFIG.get("personality", "")
    system_prompt = f"{personality}\n\n{rules}\n\n{sys_info}\n\n{memory_context}\n\n{owner_info}\nСейчас: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Мысль
    thought = f"Думаю: {username} ({'владелец' if is_owner_flag else 'зритель'}) пишет '{user_msg}'. Проверяю правила, память, характеристики. Нужно ответить коротко."
    write_thought(thought)
    
    try:
        def _call():
            return groq_client.chat.completions.create(
                model=CONFIG.get("groq_model", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.8,
                max_tokens=200
            )
        resp = await asyncio.to_thread(_call)
        answer = resp.choices[0].message.content.strip()
        print(f"[GROQ] ← {answer[:120]}...")
        
        # Парсим команды из ответа
        # [EXEC: ...]
        exec_matches = re.findall(r'\[EXEC:\s*(.*?)\]', answer)
        for cmd in exec_matches:
            cmd = cmd.strip()
            # Проверка разрешения
            if CONFIG.get("owner_sleeping") and is_owner_flag == False:
                answer += "\nНе могу выполнить, владелец ушел спать и не контролирует меня"
                continue
            if CONFIG.get("require_owner_for_dangerous") and not is_owner_flag:
                # Опасные команды только владелец
                if any(d in cmd.lower() for d in ["install", "shutdown", "reboot", "rm -rf", "apt"]):
                    answer += "\nНадо спросить разрешение у владельца для такой команды"
                    continue
            
            # Проверка безопасности
            ok2, msg2 = check_rules(cmd)
            if not ok2:
                answer = msg2
                continue
            
            # Проверка нагрузки
            if "apt install" in cmd or "install" in cmd:
                can, reason = check_if_safe_to_install(cmd)
                if not can:
                    answer = reason
                    continue
            
            # Выполняем
            out, code = await asyncio.to_thread(exec_command, cmd)
            answer += f"\n[Выполнил: {cmd} -> {out[:200]}]"
            write_memory(username, user_msg, answer, thought=thought, action=f"EXEC: {cmd} -> {out[:100]}")
        
        # [SCREEN]
        if "[SCREEN]" in answer and CONFIG.get("allow_screen"):
            path, msg = await asyncio.to_thread(take_screenshot)
            if path:
                answer += f"\n[Сделал скрин: {path}]"
                # Можно отправить в vision модель для описания
                write_memory(username, user_msg, answer, thought=thought, action=f"SCREEN: {path}")
        
        # [BROWSER: ...]
        browser_matches = re.findall(r'\[BROWSER:\s*(.*?)\]', answer)
        for q in browser_matches:
            result = await asyncio.to_thread(open_yandex_browser, q)
            answer += f"\n[{result}]"
        
        # Записываем в память
        write_memory(username, user_msg, answer, thought=thought, action=",".join(exec_matches))
        
        return answer
    except Exception as e:
        err = str(e)
        print(f"[GROQ] ❌ {err}")
        if "401" in err or "invalid" in err.lower() or "expired" in err.lower():
            set_key_expired()
            return OVERLAY_MESSAGE
        if "429" in err or "quota" in err.lower() or "limit" in err.lower():
            set_key_expired()
            return "Модель недоступна — истек ключ, владелец скоро поменяет, чат заработает"
        return f"Ошибка AI: {err[:100]}"

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=CONFIG["twitch_token"],
            prefix="!",
            initial_channels=[CONFIG["twitch_channel"]],
            heartbeat=30.0
        )
        self.msg_count = 0

    async def event_ready(self):
        print(f"✅ Подключен как {self.nick} к #{CONFIG['twitch_channel']} — РЕАЛЬНЫЙ контроль Linux, 24/7!")
        speak_async(f"Подключен к чату {CONFIG['twitch_channel']} на линуксе, реальный контроль включен!")
        self.loop.create_task(self.keepalive_task())

    async def keepalive_task(self):
        while True:
            await asyncio.sleep(60)
            print(f"💓 Keepalive — слушаю #{CONFIG['twitch_channel']} | {self.msg_count} сообщений | RAM free {SYSTEM_INFO.get('ram_available_mb')}MB")
            if not self.connected_channels:
                try:
                    await self.join_channels([CONFIG["twitch_channel"]])
                except:
                    pass

    async def event_message(self, message):
        if message.echo:
            return
        self.msg_count += 1
        username = message.author.display_name or message.author.name
        content = message.content
        badges = message.author.badges or {}
        
        owner_flag = is_owner(username, badges)
        print(f"[CHAT] {'👑 ВЛАДЕЛЕЦ' if owner_flag else '👤'} {username}: {content}")

        # Игнор команд
        if content.startswith("!") and not CONFIG.get("allow_exec"):
            return

        # Если ключ истек — показываем на оверлее
        if KEY_EXPIRED:
            update_overlay(username, content, OVERLAY_MESSAGE)
            if self.msg_count % 5 == 0:  # Не спамить голосом
                speak_async(OVERLAY_MESSAGE)
            return

        answer = await ask_groq_with_memory(content, username, owner_flag)
        if answer:
            if CONFIG.get("write_to_chat", False):
                try:
                    await message.channel.send(answer[:400])
                except:
                    pass
            update_overlay(username, content, answer)
            speak_async(answer)

start_time = time.time()

async def main():
    if not CONFIG.get("twitch_channel") or CONFIG["twitch_channel"] == "твой_канал_без_решетки":
        print("❌ Вставь twitch_channel в config.json")
        return
    if not CONFIG.get("twitch_token"):
        print("❌ Вставь twitch_token oauth:... в config.json")
        return
    if not CONFIG.get("groq_api_key") or not CONFIG["groq_api_key"].startswith("gsk_"):
        print("❌ Вставь groq_api_key gsk_... в config.json")
        return

    print("🧠 Память загружена:", len(read_recent_memory()), "записей")
    print("💭 Мысли пишутся в thoughts.txt")
    print("📸 Скрин экрана:", "доступен" if HAS_MSS else "нужен mss (pip install mss)")
    print("🖱️ Управление мышкой:", "доступно" if HAS_PYAUTOGUI else "нужен pyautogui")

    asyncio.create_task(speaker_worker())
    if CONFIG.get("show_overlay", True):
        asyncio.create_task(overlay_server())

    bot = Bot()
    while True:
        try:
            print("🚀 Запускаю бота v3 — реальный контроль Linux, память, оверлей, 24/7")
            await bot.start()
        except Exception as e:
            print(f"❌ Упал: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Остановлен")
        try:
            engine.stop()
        except:
            pass
