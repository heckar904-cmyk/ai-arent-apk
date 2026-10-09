#!/bin/bash
# Twitch AI — настоящий установщик как приложение для Linux
# Скачай этот файл и запусти: chmod +x installer.sh && ./installer.sh
# Или одной командой: curl -sL https://raw.githubusercontent.com/heckar904-cmyk/ai-arent-apk/main/twitch-ai-linux/installer.sh | bash

set -e

APP_NAME="Twitch AI"
INSTALL_DIR="$HOME/.local/share/twitch-ai"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
REPO_URL="https://github.com/heckar904-cmyk/ai-arent-apk"

echo "🎙️ $APP_NAME — установщик приложения для Linux"
echo "================================================"
echo ""

# Проверка
if [ -d "$INSTALL_DIR" ]; then
  echo "📌 Найдена старая установка в $INSTALL_DIR"
  read -p "Обновить? [Y/n]: " upd
  if [[ "$upd" =~ ^[nN] ]]; then
    echo "Отмена"
    exit 0
  fi
  echo "🔄 Обновляю, сохраняю ключи..."
  cp "$INSTALL_DIR/config.json" /tmp/twitch-ai-config.bak 2>/dev/null || true
  cp "$INSTALL_DIR/memory.jsonl" /tmp/twitch-ai-memory.bak 2>/dev/null || true
fi

echo "📦 Ставлю зависимости..."
if [ -f /etc/debian_version ]; then
  sudo apt update -qq
  sudo apt install -y python3 python3-pip python3-venv python3-tk espeak espeak-data libespeak1 ffmpeg scrot wmctrl xdotool 2>&1 | tail -3
elif [ -f /etc/arch-release ]; then
  sudo pacman -S --noconfirm python python-pip tk espeak ffmpeg scrot wmctrl xdotool
fi

echo "📥 Качаю приложение в $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"

# Качаем файлы с GitHub (последняя версия)
BASE="https://raw.githubusercontent.com/heckar904-cmyk/ai-arent-apk/main/twitch-ai-linux"
for f in main.py gui.py overlay.html requirements.txt config.json.example twitch-ai.service; do
  echo "  ⬇️ $f"
  curl -sL "$BASE/$f" -o "$INSTALL_DIR/$f" || echo "  ⚠️ $f не скачан"
done

# Восстанавливаем ключи
if [ -f /tmp/twitch-ai-config.bak ]; then
  cp /tmp/twitch-ai-config.bak "$INSTALL_DIR/config.json"
  echo "  ✅ Ключи восстановлены!"
else
  cp "$INSTALL_DIR/config.json.example" "$INSTALL_DIR/config.json" 2>/dev/null || true
fi
if [ -f /tmp/twitch-ai-memory.bak ]; then
  cp /tmp/twitch-ai-memory.bak "$INSTALL_DIR/memory.jsonl"
fi

# venv
echo "🐍 Создаю окружение..."
cd "$INSTALL_DIR"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✅ Зависимости установлены"

# Создаем лаунчер
cat > "$BIN_DIR/twitch-ai" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python3 gui.py
EOF
chmod +x "$BIN_DIR/twitch-ai"

# Создаем .desktop файл чтобы появилось в меню как приложение
cat > "$DESKTOP_DIR/twitch-ai.desktop" << EOF
[Desktop Entry]
Name=Twitch AI
Comment=AI бот для Twitch — только голос + текст на стриме, 24/7, реальный контроль Linux
Exec=$BIN_DIR/twitch-ai
Icon=audio-x-generic
Terminal=false
Type=Application
Categories=AudioVideo;Network;
Keywords=twitch;ai;bot;voice;
StartupNotify=true
Path=$INSTALL_DIR
EOF

chmod +x "$DESKTOP_DIR/twitch-ai.desktop"

# Обновляем базу приложений
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ""
echo "✅ Установлено как настоящее приложение!"
echo ""
echo "👉 Как запустить:"
echo "  1. Нажми Super (Win) и напиши 'Twitch AI' — появится иконка, кликни!"
echo "  2. Или в терминале: twitch-ai"
echo "  3. Или: ~/.local/bin/twitch-ai"
echo ""
echo "📁 Папка приложения: $INSTALL_DIR"
echo "⚙️ Конфиг с ключами: $INSTALL_DIR/config.json"
echo "🔄 Автообновление: в приложении кнопка 'Автообновление' — само скачает с сервера!"
echo ""
echo "🗑️ Удалить: rm -rf $INSTALL_DIR ~/.local/bin/twitch-ai ~/.local/share/applications/twitch-ai.desktop"
echo ""
echo "Запускаю приложение..."
"$BIN_DIR/twitch-ai" &
