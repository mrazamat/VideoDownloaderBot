import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, Message

from .config import load_config
from .downloader import HAS_FFMPEG, DownloadError, download, find_supported_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

config = load_config()
dp = Dispatcher()
semaphore = asyncio.Semaphore(config.max_concurrent)

HELP_TEXT = (
    "👋 Пришлите ссылку на видео, и я отправлю его вам.\n\n"
    "Поддерживаются:\n"
    "• YouTube (включая Shorts)\n"
    "• X / Twitter\n"
    "• Instagram (Reels, посты)\n"
    "• Facebook (видео, Reels)\n\n"
    f"Максимальный размер файла: {config.max_file_size // (1024 * 1024)} МБ."
)


def is_allowed(message: Message) -> bool:
    return not config.allowed_users or (
        message.from_user is not None and message.from_user.id in config.allowed_users
    )


@dp.message(CommandStart())
@dp.message(Command("help"))
async def cmd_start(message: Message) -> None:
    await message.answer(HELP_TEXT)


@dp.message(F.text | F.caption)
async def handle_link(message: Message, bot: Bot) -> None:
    if not is_allowed(message):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return

    found = find_supported_url(message.text or message.caption or "")
    if not found:
        await message.answer("Не нашёл ссылку на YouTube, X, Instagram или Facebook.")
        return
    url, platform = found

    status = await message.reply(f"⏳ Скачиваю видео с {platform}…")
    video = None
    try:
        async with semaphore:
            await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
            video = await asyncio.to_thread(
                download, url, config.download_dir, config.max_file_size, config.cookies_file
            )
            await status.edit_text("📤 Отправляю…")
            await bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
            await message.reply_video(
                FSInputFile(video.path, filename=video.path.name),
                caption=video.title[:1000],
                duration=video.duration,
                width=video.width,
                height=video.height,
                supports_streaming=True,
                request_timeout=600,
            )
        await status.delete()
    except DownloadError as e:
        await status.edit_text(f"❌ {e}")
    except Exception:
        log.exception("Ошибка при обработке %s", url)
        await status.edit_text("❌ Произошла ошибка. Попробуйте позже.")
    finally:
        if video:
            video.cleanup()


async def main() -> None:
    session = None
    if config.api_url:
        session = AiohttpSession(api=TelegramAPIServer.from_base(config.api_url, is_local=True))
    bot = Bot(token=config.bot_token, session=session)
    if not HAS_FFMPEG:
        log.warning("ffmpeg не найден — качество YouTube будет ограничено. Установите ffmpeg.")
    log.info("Бот запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
