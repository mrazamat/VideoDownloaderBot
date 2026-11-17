import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    allowed_users: frozenset[int]
    max_concurrent: int
    cookies_file: Path | None
    api_url: str | None
    download_dir: Path

    @property
    def max_file_size(self) -> int:
        # Публичный Bot API позволяет ботам отправлять файлы до 50 МБ,
        # локальный сервер Bot API — до 2 ГБ.
        return (2000 if self.api_url else 50) * 1024 * 1024


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен.")

    users = {
        int(u) for u in os.getenv("ALLOWED_USERS", "").replace(" ", "").split(",") if u
    }
    cookies = os.getenv("COOKIES_FILE", "").strip()
    cookies_path = Path(cookies) if cookies else None
    if cookies_path and not cookies_path.is_file():
        raise SystemExit(f"COOKIES_FILE не найден: {cookies_path}")

    download_dir = Path(os.getenv("DOWNLOAD_DIR", "downloads")).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=token,
        allowed_users=frozenset(users),
        max_concurrent=max(1, int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))),
        cookies_file=cookies_path,
        api_url=os.getenv("TELEGRAM_API_URL", "").strip() or None,
        download_dir=download_dir,
    )
