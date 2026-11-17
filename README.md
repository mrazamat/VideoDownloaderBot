# Video Downloader Bot

Телеграм-бот, который скачивает видео по ссылке с **YouTube**, **X (Twitter)**, **Instagram** и **Facebook** и присылает его в чат.

Стек: Python 3.11+, [aiogram 3](https://docs.aiogram.dev/), [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Быстрый старт (Docker, рекомендуется)

1. Создайте бота у [@BotFather](https://t.me/BotFather) и получите токен.
2. `cp .env.example .env` и впишите `BOT_TOKEN`.
3. `docker compose up -d --build`

ffmpeg и deno в образе уже есть.

## Запуск без Docker

Нужны системные зависимости:
- **ffmpeg**: склеивает видео и аудио (YouTube отдаёт их раздельно). `sudo apt install ffmpeg`
- **deno**: JS-движок, без которого yt-dlp не может получить форматы YouTube. `curl -fsSL https://deno.land/install.sh | sh`

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # впишите BOT_TOKEN
.venv/bin/python -m bot.main
```

## Использование

Отправьте боту ссылку (можно вместе с текстом), и он ответит видеофайлом. Команды: `/start`, `/help`.

## Настройки (`.env`)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота (обязательно) |
| `ALLOWED_USERS` | ID пользователей через запятую; пусто = бот доступен всем |
| `MAX_CONCURRENT_DOWNLOADS` | Сколько загрузок идёт одновременно (по умолчанию 3) |
| `COOKIES_FILE` | Путь к cookies.txt (формат Netscape) |
| `TELEGRAM_API_URL` | Адрес локального Bot API сервера, снимает лимит 50 МБ |

## Ограничения и советы

- **Лимит 50 МБ.** Через обычный Bot API бот не может отправить файл больше 50 МБ, поэтому бот выбирает лучшее качество, которое укладывается в лимит. Чтобы отправлять файлы до 2 ГБ, поднимите [telegram-bot-api](https://github.com/tdlib/telegram-bot-api) и задайте `TELEGRAM_API_URL`.
- **Instagram / Facebook** часто требуют вход в аккаунт, особенно с IP серверов. Экспортируйте cookies из браузера (расширение «Get cookies.txt LOCALLY»), положите файл рядом и укажите `COOKIES_FILE`. Лучше используйте отдельный аккаунт.
- **Обновляйте yt-dlp.** Сайты часто меняются: `pip install -U "yt-dlp[default]"` или `docker compose build --no-cache`.
- Скачивайте только контент, на который у вас есть права, и соблюдайте правила платформ.
