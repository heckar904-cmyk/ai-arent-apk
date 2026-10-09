# 🎙️ Twitch AI Voice Bot для Linux — 24/7, Groq + голос, не отваливается

**Что делает:**
- Слушает твой Twitch чат 24/7 через TwitchIO (IRC), **не отключается** если 5 минут никто не пишет (в отличие от Copilot на Windows)
- Когда кто-то пишет — отправляет в Groq (gsk_... llama-3.3-70b) и отвечает в чат + **говорит голосом** через espeak/pyttsx3 прямо из системы
- Голос стандартный из Linux, бесплатно, без API
- Если кончатся кредиты Groq — меняешь ключ вручную в config.json и `systemctl restart twitch-ai`
- Может управлять компом если включишь `allow_exec` (выполняет `!exec команда`)

**Для Linux, без сайтов, без Replit, без сервисов которые ты ненавидишь.**

---

## 🚀 Быстрая установка (Ubuntu/Debian/Mint)

```bash
git clone https://github.com/heckar904-cmyk/ai-arent-apk.git
cd ai-arent-apk/twitch-ai-linux   # или скачай папку twitch-ai-linux отдельно
chmod +x install.sh
./install.sh
```

Скрипт поставит:
- `espeak`, `ffmpeg`, `python3-venv`
- создаст `venv` и поставит `twitchio groq pyttsx3`

### 1. Получи токены

**Twitch:**
1. Иди на https://twitchtokengenerator.com
2. Выбери **Bot Chat Token**
3. Авторизуйся, скопируй `oauth:....`

**Groq (тот самый Grog с Q):**
1. Иди на https://console.groq.com/keys
2. Create API Key
3. Скопируй `gsk_...` — бесплатно 14k запросов/день

### 2. Настрой config.json

```bash
cp config.json.example config.json
nano config.json
```

Вставь:
```json
{
  "twitch_channel": "твой_канал_без_#",
  "twitch_token": "oauth:твой_токен",
  "twitch_nick": "твой_ник_бота",
  "groq_api_key": "gsk_...",
  "bot_name": "AI",
  "personality": "Ты веселый AI...",
  "reply_all": true,
  "mention_only": false
}
```

- `reply_all: true` — отвечает на каждое сообщение
- `mention_only: true` — только если упомянули имя бота
- `allow_exec: false` — если true, то `!exec ls` выполнит команду на компе (осторожно!)

### 3. Запуск вручную (тест)

```bash
source venv/bin/activate
python3 main.py
```

Должно написать:
```
✅ Подключен как твой_бот к #твой_канал — слушаю 24/7, не отключусь!
🔊 Говорю: Подключен к чату...
```

Попроси друга написать в чат — бот ответит в чат + голосом!

### 4. 24/7 режим (чтобы не отваливался)

Чтобы бот работал постоянно, даже после перезагрузки и не отключался после 5 мин тишины:

```bash
# Скопируй сервис (замени %i на свой юзер, или отредактируй файл)
sudo cp twitch-ai.service /etc/systemd/system/twitch-ai@твой_юзер.service
# или если юзер одинаковый:
sudo cp twitch-ai.service /etc/systemd/system/twitch-ai.service
# и внутри поменяй /home/%i на /home/твой_юзер

sudo systemctl daemon-reload
sudo systemctl enable --now twitch-ai
# или с @
sudo systemctl enable --now twitch-ai@твой_юзер

# Проверить
sudo systemctl status twitch-ai
journalctl -u twitch-ai -f
```

Теперь бот:
- Запускается при включении компа
- Если упадет — перезапускается через 5 сек (`Restart=always`)
- Keepalive пинг каждые 60 сек, пишет в лог `💓 Keepalive — всё ещё слушаю`
- Не отключается если никто не пишет

Остановить:
```bash
sudo systemctl stop twitch-ai
sudo systemctl disable twitch-ai
```

---

## 🔊 Голос

Используется `pyttsx3` + `espeak` — оффлайн, бесплатно.

Проверить голоса:
```bash
python3 -c "import pyttsx3; e=pyttsx3.init(); print(e.getProperty('voices'))"
espeak --voices
```

Русские голоса:
```bash
sudo apt install espeak-data mbrola mbrola-ru1
# или
sudo apt install espeak-ng
```

В `config.json`:
- `voice_rate`: 180 (скорость)
- `voice_volume`: 0.9
- `voice_id`: null (авто русский) или индекс из списка

Тест голоса:
```bash
espeak "Привет я твой бот"
python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('Привет! Я на линуксе'); e.runAndWait()"
```

---

## 🖥️ Полный доступ к компу

Если `allow_exec: true`, бот выполняет команды из чата:

В чате пишут:
```
!exec ls ~/Videos
!exec shutdown -h +10
```

Бот выполнит через `subprocess` и ответит результатом в чат + голосом.

**Осторожно!** Любой в чате сможет выполнить команду. Включай только если доверяешь чату или сделай фильтр по никам в коде.

---

## ❓ FAQ

**Q: Отключается через 5 мин как копайлот?**
A: Нет! У нас `heartbeat=30`, keepalive каждые 60с, `Restart=always` в systemd. Даже если твич отвалится — реконнект через 3с.

**Q: Groq кончились кредиты?**
A: В логе будет `429` или `quota`. Иди на console.groq.com/keys → создай новый `gsk_...` → вставь в config.json → `sudo systemctl restart twitch-ai`

**Q: Нет звука?**
A: `sudo apt install pulseaudio alsa-utils`, проверь `espeak test`, проверь `pavucontrol` что не мьют.

**Q: Хочу другой голос, нейросетевой?**
A: Замени pyttsx3 на Piper TTS (`pip install piper-tts`) или gTTS. В коде функция `speak_blocking` — поменяй на свою.

**Q: Работает на Arch/Manjaro?**
A: Да, `install.sh` определяет Arch и ставит через pacman.

---

## 📁 Структура

```
twitch-ai-linux/
  main.py — основной бот
  requirements.txt — зависимости
  config.json.example — пример конфига
  config.json — твой конфиг (не коммить!)
  install.sh — установка одной командой
  twitch-ai.service — systemd для 24/7
  README.md — эта инструкция
```

---

Готово! Теперь у тебя AI на Linux который постоянно слушает твич чат и отвечает голосом, без сайтов и без сервисов которые ты ненавидишь.
