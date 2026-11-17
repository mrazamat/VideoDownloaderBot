import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

SUPPORTED_DOMAINS = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "x.com": "X",
    "twitter.com": "X",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
    "fb.com": "Facebook",
}

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
HOST_RE = re.compile(r"https?://(?:[a-z0-9-]+\.)*?([a-z0-9-]+\.[a-z]{2,})(?:[/:?#]|$)", re.IGNORECASE)

HAS_FFMPEG = shutil.which("ffmpeg") is not None


class DownloadError(Exception):
    """Ошибка с текстом, который можно показать пользователю."""


@dataclass
class DownloadedVideo:
    path: Path
    title: str
    duration: int | None
    width: int | None
    height: int | None
    workdir: Path

    def cleanup(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)


def find_supported_url(text: str) -> tuple[str, str] | None:
    """Возвращает (url, название платформы) для первой поддерживаемой ссылки."""
    for url in URL_RE.findall(text or ""):
        m = HOST_RE.match(url)
        if m and (platform := SUPPORTED_DOMAINS.get(m.group(1).lower())):
            return url, platform
    return None


def _format_selector(max_bytes: int) -> str:
    limit = f"{max_bytes // (1024 * 1024)}M"
    # `<?` — пропускать форматы с неизвестным размером, а не отбрасывать их.
    if HAS_FFMPEG:
        # Сначала H.264 (avc1) — его воспроизводят все клиенты Telegram, в отличие от AV1/VP9.
        return (
            f"bv*[vcodec^=avc][filesize<?{limit}]+ba[ext=m4a]/"
            f"bv*[ext=mp4][filesize<?{limit}]+ba[ext=m4a]/"
            f"b[ext=mp4][filesize<?{limit}]/"
            f"bv*[filesize<?{limit}]+ba/"
            f"b[filesize<?{limit}]/b"
        )
    # Без ffmpeg нельзя склеить отдельные видео- и аудиодорожки.
    return f"b[ext=mp4][filesize<?{limit}]/b[filesize<?{limit}]/b"


def download(url: str, base_dir: Path, max_bytes: int, cookies: Path | None = None) -> DownloadedVideo:
    """Синхронно скачивает видео. Запускать в отдельном потоке."""
    workdir = Path(tempfile.mkdtemp(dir=base_dir))
    opts = {
        "format": _format_selector(max_bytes),
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "playlist_items": "1",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "restrictfilenames": True,
        "max_filesize": max_bytes,
        "socket_timeout": 30,
        "retries": 3,
    }
    if HAS_FFMPEG:
        opts["merge_output_format"] = "mp4"
    if cookies:
        opts["cookiefile"] = str(cookies)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        shutil.rmtree(workdir, ignore_errors=True)
        raise DownloadError(_humanize(str(e))) from e
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise

    if info and info.get("entries"):
        info = next((e for e in info["entries"] if e), info)

    files = [p for p in workdir.iterdir() if p.is_file() and not p.name.endswith(".part")]
    if not files:
        shutil.rmtree(workdir, ignore_errors=True)
        raise DownloadError("Видео слишком большое или не найдено в этой публикации.")

    path = max(files, key=lambda p: p.stat().st_size)
    if path.stat().st_size > max_bytes:
        shutil.rmtree(workdir, ignore_errors=True)
        raise DownloadError(
            f"Файл больше {max_bytes // (1024 * 1024)} МБ — Telegram не позволяет его отправить."
        )

    return DownloadedVideo(
        path=path,
        title=(info or {}).get("title") or "video",
        duration=int(d) if (d := (info or {}).get("duration")) else None,
        width=(info or {}).get("width"),
        height=(info or {}).get("height"),
        workdir=workdir,
    )


def _humanize(err: str) -> str:
    low = err.lower()
    if "login" in low or "cookies" in low or "sign in" in low:
        return "Сайт требует авторизацию. Добавьте cookies (см. COOKIES_FILE в README)."
    if "private" in low:
        return "Это приватное видео — доступ к нему закрыт."
    if "unsupported url" in low:
        return "Ссылка не поддерживается."
    if "no video" in low or "no media" in low:
        return "В этой публикации нет видео."
    if "unavailable" in low or "removed" in low or "404" in low:
        return "Видео недоступно или удалено."
    if "requested format is not available" in low:
        return "Нет подходящего формата нужного размера."
    return "Не удалось скачать видео."
