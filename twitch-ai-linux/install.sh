#!/bin/bash
# Twitch AI v3 — умная установка/обновление/удаление
# Само проверяет установлено или нет

set -e

INSTALL_DIR="$HOME/twitch-ai-linux"
SERVICE_NAME="twitch-ai"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "🎙️ Twitch AI v3 — проверка и установка"
echo "======================================="

# Функция проверки установлено ли
check_installed() {
  echo "🔍 Проверяю установлено ли..."
  local installed=false
  
  if [ -d "$INSTALL_DIR" ]; then
    echo "  ✅ Папка $INSTALL_DIR найдена"
    installed=true
    if [ -f "$INSTALL_DIR/config.json" ]; then
      echo "  ✅ config.json есть (ключи сохранены)"
      # Показать канал без ключа
      channel=$(python3 -c "import json; print(json.load(open('$INSTALL_DIR/config.json')).get('twitch_channel','?'))" 2>/dev/null || echo "?")
      echo "     Канал: $channel"
    else
      echo "  ⚠️ config.json нет"
    fi
    if [ -d "$INSTALL_DIR/venv" ]; then
      echo "  ✅ venv есть"
    fi
  else
    echo "  ❌ Папка $INSTALL_DIR не найдена — не установлено"
  fi

  if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    echo "  ✅ Systemd сервис $SERVICE_NAME найден"
    systemctl is-active --quiet $SERVICE_NAME && echo "     Статус: 🟢 Работает 24/7" || echo "     Статус: 🔴 Остановлен"
    installed=true
  else
    echo "  ❌ Systemd сервис не найден"
  fi

  if pgrep -f "twitch-ai-linux.*main.py" > /dev/null; then
    echo "  ✅ Процесс main.py работает прямо сейчас"
    installed=true
  fi

  if $installed; then
    echo ""
    echo "📌 ВЫВОД: Установлено!"
    return 0
  else
    echo ""
    echo "📌 ВЫВОД: Не установлено"
    return 1
  fi
}

# Если запустили с аргументом
if [ "$1" == "check" ] || [ "$1" == "--check" ]; then
  check_installed
  exit 0
fi

if [ "$1" == "uninstall" ] || [ "$1" == "--uninstall" ] || [ "$1" == "delete" ]; then
  echo "🗑️ Удаление..."
  sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
  sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
  sudo rm -f $SERVICE_FILE
  sudo systemctl daemon-reload
  rm -rf "$INSTALL_DIR"
  echo "✅ Удалено! Папка $INSTALL_DIR и сервис удалены"
  exit 0
fi

# Проверяем установлено ли
if check_installed; then
  echo ""
  echo "Что делаем?"
  echo "  [U] Обновить (сохранит config.json с ключами)"
  echo "  [R] Переустановить полностью (удалит всё и поставит заново)"
  echo "  [D] Удалить"
  echo "  [C] Отмена"
  read -p "Выбери U/R/D/C: " choice
  case "$choice" in
    U|u)
      echo "🔄 Обновление..."
      # Бэкап config.json
      cp "$INSTALL_DIR/config.json" /tmp/config.json.bak 2>/dev/null || echo "⚠️ config.json не найден, будет создан новый"
      # Бэкап памяти
      cp "$INSTALL_DIR/memory.jsonl" /tmp/memory.jsonl.bak 2>/dev/null || true
      cp "$INSTALL_DIR/thoughts.txt" /tmp/thoughts.txt.bak 2>/dev/null || true
      
      # Копируем новые файлы (этот скрипт должен быть в новой версии)
      SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
      if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
        echo "  Копирую файлы из $SCRIPT_DIR в $INSTALL_DIR..."
        cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR"/ 2>/dev/null || true
      fi
      
      # Восстанавливаем config
      if [ -f /tmp/config.json.bak ]; then
        cp /tmp/config.json.bak "$INSTALL_DIR/config.json"
        echo "  ✅ config.json восстановлен (ключи сохранены)"
      fi
      if [ -f /tmp/memory.jsonl.bak ]; then
        cp /tmp/memory.jsonl.bak "$INSTALL_DIR/memory.jsonl"
        echo "  ✅ Память восстановлена (помнит вчера)"
      fi
      
      cd "$INSTALL_DIR"
      source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
      pip install --upgrade pip -q
      pip install -r requirements.txt -q
      echo "  ✅ Зависимости обновлены"
      
      # Перезапуск сервиса если был
      if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
        sudo systemctl restart $SERVICE_NAME
        echo "  ✅ Сервис перезапущен"
      fi
      
      echo "✅ Обновлено! Запусти: cd $INSTALL_DIR && source venv/bin/activate && python3 main.py"
      exit 0
      ;;
    R|r)
      echo "🔄 Переустановка..."
      sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
      sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
      sudo rm -f $SERVICE_FILE
      rm -rf "$INSTALL_DIR"
      echo "  Старое удалено, ставлю заново..."
      # Продолжаем как новая установка
      ;;
    D|d)
      exec "$0" uninstall
      ;;
    C|c|*)
      echo "Отмена"
      exit 0
      ;;
  esac
fi

# Новая установка
echo ""
echo "📦 Новая установка..."

# Зависимости системы
if [ -f /etc/debian_version ]; then
  echo "  Ставлю espeak ffmpeg scrot wmctrl xdotool..."
  sudo apt update -qq
  sudo apt install -y python3 python3-pip python3-venv espeak espeak-data libespeak1 ffmpeg alsa-utils pulseaudio scrot wmctrl xdotool 2>&1 | tail -5
elif [ -f /etc/arch-release ]; then
  sudo pacman -S --noconfirm python python-pip espeak ffmpeg scrot wmctrl xdotool
fi

# Копируем в HOME если запускаем из другого места
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
  echo "  Копирую в $INSTALL_DIR..."
  mkdir -p "$INSTALL_DIR"
  cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR"/
fi

cd "$INSTALL_DIR"
echo "  Создаю venv..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ ! -f config.json ]; then
  cp config.json.example config.json
  echo "  ✅ Создан config.json — отредактируй!"
fi

touch memory.jsonl thoughts.txt

echo ""
echo "🔊 Тест голоса..."
python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('Привет! Я AI v3'); e.runAndWait()" 2>&1 | head -3 || echo "  ⚠️ Голос: проверь espeak"

echo ""
echo "✅ Установлено в $INSTALL_DIR!"
echo ""
echo "👉 Дальше:"
echo "1. nano $INSTALL_DIR/config.json — вставь канал и ключи (только channel, token, gsk_...)"
echo "2. cd $INSTALL_DIR && source venv/bin/activate && python3 main.py"
echo "3. Для 24/7 (не отваливается):"
echo "   sudo cp twitch-ai.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload && sudo systemctl enable --now twitch-ai"
echo "   journalctl -u twitch-ai -f"
echo ""
echo "Проверка: $0 check"
echo "Удаление: $0 uninstall"
