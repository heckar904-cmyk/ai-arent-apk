#!/bin/bash
# Быстрое удаление

echo "🗑️ Удаляю Twitch AI..."
sudo systemctl stop twitch-ai 2>/dev/null || true
sudo systemctl disable twitch-ai 2>/dev/null || true
sudo rm -f /etc/systemd/system/twitch-ai.service
sudo systemctl daemon-reload
rm -rf ~/twitch-ai-linux
rm -rf ~/twitch-ai-linux-v3
echo "✅ Удалено! Проверь: ls ~/ | grep twitch"
