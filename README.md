# ComfyUI-Agent

Локальный аналог встроенного **Comfy Agent** для ComfyUI: боковая панель с ИИ-агентом, который видит холст, строит и правит воркфлоу, проверяет граф и запускает генерации.

Расширение находится в папке [`ComfyUI-Agent/`](ComfyUI-Agent/), полное описание и возможности — в [`ComfyUI-Agent/README.md`](ComfyUI-Agent/README.md).

## Установка

```bash
git clone https://github.com/CrazyDashTool/ComfyUI-Agent.git
```

Затем скопируй вложенную папку `ComfyUI-Agent/ComfyUI-Agent` в `ComfyUI/custom_nodes/` и перезапусти ComfyUI.

Дополнительные зависимости не нужны: используется `aiohttp`, который уже есть в ComfyUI. Для агента нужна модель с поддержкой tool calling; для vision — мультимодальная.

## Настройка

Открой панель агента в ComfyUI, нажми ⚙ и укажи провайдера, ключ и модель. Поддерживаются OpenAI-совместимые API (OpenAI, Gemini, OpenRouter, DeepSeek, Groq, Ollama, LM Studio и другие) и Anthropic.

Ключ хранится локально в `ComfyUI-Agent/config.json` и не попадает в git.

## Лицензия

[Apache License 2.0](LICENSE)
