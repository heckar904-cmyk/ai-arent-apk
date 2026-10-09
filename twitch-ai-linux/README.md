# 🎙️ Twitch AI Voice Bot для Linux — только голос + текст на стриме, не пишет в чат

**Что делает (как ты хотел ВСЕЕЕ):**
- ✅ Читает сообщения из Twitch чата (нужен только канал + oauth токен)
- ❌ **НЕ пишет в чат** — только говорит голосом (write_to_chat=false)
- 🔊 Говорит голосом через espeak/pyttsx3 (оффлайн, бесплатно)
- 🖥️ Выдает текст на стриме — оверлей для OBS `http://localhost:8080/overlay.html`
- 24/7 — не отключается после 5 мин тишины, keepalive 60с, авто-реконнект
- Groq gsk_... llama-3.3-70b

**Никакого twitch_nick больше не нужно! Убрал!**

---

## Установка

```bash
unzip twitch-ai-linux.zip
cd twitch-ai-linux
chmod +x install.sh && ./install.sh
```

## Настройка config.json

```bash
cp config.json.example config.json
nano config.json
```

Вставь:

```json
{
  "twitch_channel": "твой_канал_без_#",
  "twitch_token": "oauth:zy...твой_access_token",
  "groq_api_key": "gsk_9...E",
  "write_to_chat": false,
  "show_overlay": true,
  "overlay_port": 8080,
  "reply_all": true,
  "mention_only": false
}
```

- `twitch_channel` — твой ник на твиче без #
- `twitch_token` — твой Access token с `oauth:` в начале (zy... → oauth:zy...)
- `groq_api_key` — gsk_... с console.groq.com/keys
- `write_to_chat: false` — НЕ пишет в чат, только голос (как ты хотел!)
- `show_overlay: true` — включает оверлей для OBS

Client ID и Refresh token не нужны для этого бота.

## Запуск

```bash
source venv/bin/activate
python3 main.py
```

Увидишь:
```
✅ Подключен к #канал — слушаю 24/7
🖥️ Оверлей для OBS: http://localhost:8080/overlay.html
```

## Текст на стриме (OBS)

1. В OBS → Добавить источник → Browser Source
2. URL: `http://localhost:8080/overlay.html`
3. Размер: 900x250
4. Поставь галочку Shutdown source when not visible = OFF, чтобы работал всегда
5. Когда кто-то пишет в чат — на стриме появится плашка:
   ```
   Username спросил: "привет"
   Привет! Я AI на линуксе...
   ```

Плашка показывается 12 сек, потом скрывается.

Если хочешь проверить без OBS — просто открой http://localhost:8080/overlay.html в браузере.

## Голос

- Работает через espeak, оффлайн
- Тест: `espeak "привет"`
- Смена голоса в config.json: `voice_rate`, `voice_volume`

## 24/7

```bash
sudo cp twitch-ai.service /etc/systemd/system/twitch-ai.service
sudo systemctl daemon-reload
sudo systemctl enable --now twitch-ai
journalctl -u twitch-ai -f
```

Не отваливается после 5 мин тишины — keepalive каждые 60с.

## Удаление

```bash
sudo systemctl stop twitch-ai
sudo systemctl disable twitch-ai
sudo rm /etc/systemd/system/twitch-ai.service
rm -rf ~/twitch-ai-linux
```

Готово — только голос + текст на стриме, без записи в чат!
