# Модели с Hugging Face - локально на телефоне

Все модели качаются при первом запуске через Transformers.js и работают оффлайн.

## Whisper Tiny - Audio Agent

- **HF**: `Xenova/whisper-tiny` (квантованная `openai/whisper-tiny`)
- **Размер**: 39MB
- **Зачем**: Речь в текст, ищет тишину и "эээ", делает VAD
- **Использование**:
```js
import { pipeline } from '@xenova/transformers'
const whisper = await pipeline('automatic-speech-recognition', 'Xenova/whisper-tiny')
const text = await whisper(audioBlob)
```

## CLIP ViT Base - оценка кадров

- **HF**: `Xenova/clip-vit-base-patch32` (`openai/clip-vit-base-patch32`)
- **Размер**: 150MB
- **Зачем**: Оценивает качество кадров, выбирает лучшие дубли, убирает размытые
- **Код**:
```js
const clip = await pipeline('image-classification', 'Xenova/clip-vit-base-patch32')
```

## Moondream2 - Vision Agent

- **HF**: `Xenova/moondream2` (версия `vikhyatk/moondream2`)
- **Размер**: 400MB квантованный
- **Зачем**: Описывает что на видео одним предложением, как человек
- **В APK**: через onnxruntime

## Llama 3.2 3B - Director Agent

- **HF**: `mlc-ai/Llama-3.2-3B-Instruct-q4f32_1-MLC`
- **Размер**: 2GB q4
- **Зачем**: Директор монтажа, принимает данные от Vision и Audio и решает порядок, где резать, какие эффекты
- **Код**:
```js
import { CreateMLCEngine } from '@mlc-ai/web-llm'
const engine = await CreateMLCEngine('Llama-3.2-3B-Instruct-q4f32_1-MLC')
const plan = await engine.chat.completions.create({
  messages: [{role:"user", content: "Смонтируй видео: убери тишину, выбери лучшие дубли"}]
})
```

## FFmpeg

- **Web**: `@ffmpeg/ffmpeg` wasm 30MB
- **APK**: `ffmpeg-kit` нативный, быстрее
- **Зачем**: Режет по таймкодам от Whisper, применяет crop 88% linear, scale 1920:1080, fps 24, zoompan для фото, склеивает

## Как работают вместе (режим АГЕНТ)

```
[Выбранные видео]
  -> Vision Agent (Moondream2) -> описания
  -> CLIP Agent -> оценка качества
  -> Audio Agent (Whisper) -> транскрипт + таймкоды тишины
  -> Director Agent (Llama) -> JSON план монтажа
  -> FFmpeg -> финальное видео
```

Все агенты включаются/выключаются в UI, можно выбирать какие ИИ использовать.

## Lite режим для слабых телефонов

Только Whisper Tiny 39MB + FFmpeg 30MB = 70MB
Без Llama и Moondream, план монтажа по эвристике (громкость, резкость)

## Скачать вручную

```bash
pip install huggingface_hub
huggingface-cli download Xenova/whisper-tiny --local-dir ./models/whisper
huggingface-cli download Xenova/clip-vit-base-patch32 --local-dir ./models/clip
```

В APK качаются автоматически через Cache Storage.
