#!/bin/bash
set -e
echo "🎙️ Twitch AI v3 — РЕАЛЬНЫЙ контроль Linux — установка"
echo "====================================================="

if [ -f /etc/debian_version ]; then
  echo "📦 Debian/Ubuntu — ставлю зависимости для реального контроля"
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv espeak espeak-data libespeak1 ffmpeg alsa-utils pulseaudio scrot wmctrl xdotool yandex-browser || echo "yandex-browser не найден, будет firefox"
  # Для скриншотов и мышки
  sudo apt install -y python3-tk python3-dev scrot
elif [ -f /etc/arch-release ]; then
  sudo pacman -S --noconfirm python python-pip espeak ffmpeg scrot wmctrl xdotool
else
  echo "⚠️ Поставь вручную: espeak ffmpeg scrot wmctrl xdotool"
fi

echo "🐍 venv..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f config.json ]; then
  cp config.json.example config.json
  echo "✅ Создан config.json — отредактируй!"
else
  echo "ℹ️ config.json уже есть"
fi

# Создаем пустые файлы памяти
touch memory.jsonl thoughts.txt
echo "🧠 Созданы memory.jsonl (память) и thoughts.txt (мысли)"

echo ""
echo "🔊 Тест голоса..."
python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('Привет! Я AI v3 с реальным контролем линукса'); e.runAndWait()" || echo "⚠️ Голос: espeak test"

echo ""
echo "📸 Тест скрина..."
python3 -c "import mss; print('mss ok')" || echo "⚠️ mss не работает"

echo ""
echo "✅ v3 готово! Что нового:"
echo "- Реальный контроль: команды, скрин, браузер"
echo "- Память в memory.jsonl — помнит вчера/позавчера даже после переустановки"
echo "- Мысли в thoughts.txt"
echo "- Характеристики системы в system_info.json"
echo "- Оверлей с сообщением если ключ истек"
echo "- Понимает кто главный в чате (broadcaster)"
echo "- Правила: no 112 (шутит), no 18+, no вирусы"
echo ""
echo "👉 Дальше:"
echo "1. nano config.json — вставь twitch_channel, oauth:токен, gsk_..."
echo "   Вставь только channel, token, groq_api_key — остальное уже настроено!"
echo "   write_to_chat=false — только голос + оверлей как ты хотел"
echo "2. source venv/bin/activate && python3 main.py"
echo "3. В OBS: Browser Source -> http://localhost:8080/overlay.html (900x250)"
echo "4. 24/7: sudo cp twitch-ai.service /etc/systemd/system/ && sudo systemctl enable --now twitch-ai"
echo ""
echo "Удаление: sudo systemctl stop twitch-ai; rm -rf ~/twitch-ai-linux-v3"
