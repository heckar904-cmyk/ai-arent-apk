#!/bin/bash
# Twitch AI Voice Bot — установка на Linux (Ubuntu/Debian/Mint/Arch)
# Запуск: chmod +x install.sh && ./install.sh

set -e

echo "🎙️ Twitch AI Voice Bot — установка для Linux"
echo "=============================================="

# Определяем дистрибутив
if [ -f /etc/debian_version ]; then
  echo "📦 Debian/Ubuntu обнаружен — ставлю espeak, ffmpeg, python3-venv"
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv espeak espeak-data libespeak1 ffmpeg alsa-utils pulseaudio
elif [ -f /etc/arch-release ]; then
  echo "📦 Arch обнаружен"
  sudo pacman -S --noconfirm python python-pip espeak ffmpeg
else
  echo "⚠️ Неизвестный дистр, пробую ставить через pip, но espeak поставь вручную: sudo apt install espeak ffmpeg"
fi

echo ""
echo "🐍 Создаю venv..."
python3 -m venv venv
source venv/bin/activate

echo "📥 Ставлю зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "⚙️ Настройка конфига..."
if [ ! -f config.json ]; then
  cp config.json.example config.json
  echo "✅ Создан config.json из примера"
else
  echo "ℹ️ config.json уже есть, не трогаю"
fi

echo ""
echo "🔊 Тестирую голос..."
python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('Привет! Я твой Twitch AI бот на линуксе, готов слушать чат 24 на 7'); e.runAndWait()" || echo "⚠️ Голос не сработал, проверь espeak: espeak 'test'"

echo ""
echo "✅ Установка готова!"
echo ""
echo "👉 Дальше:"
echo "1. Получи токены:"
echo "   - Twitch: https://twitchtokengenerator.com → Bot Chat Token → скопируй oauth:... "
echo "   - Groq: https://console.groq.com/keys → Create API Key → gsk_..."
echo "2. Отредактируй config.json:"
echo "   nano config.json"
echo "   Вставь: twitch_channel, twitch_token, groq_api_key"
echo "3. Запусти:"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "4. Для 24/7 (чтобы не отваливался после 5 мин тишины как копайлот):"
echo "   sudo cp twitch-ai.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable --now twitch-ai"
echo "   sudo systemctl status twitch-ai"
echo "   journalctl -u twitch-ai -f (логи)"
echo ""
echo "Готово! Бот будет слушать чат постоянно и отвечать голосом."
