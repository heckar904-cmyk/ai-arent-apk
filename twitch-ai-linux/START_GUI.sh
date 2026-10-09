#!/bin/bash
# Двойной клик — запускает GUI приложение с кнопками
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  echo "Первый запуск — ставлю зависимости..."
  ./install.sh
fi
source venv/bin/activate
python3 gui.py
