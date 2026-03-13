import httpx
import logging
import os
import tempfile
from typing import Optional
from app.multimodal.ocr import extract_text_from_image
from app.multimodal.transcribe import transcribe_audio

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

async def download_file(url: str, dest_path: str) -> bool:
    """Download a file from URL, return False if too large or failed."""
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, timeout=30) as response:
                response.raise_for_status()

                # Check content length before downloading
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_FILE_SIZE:
                    logger.warning(f"Skipping {url} — file size {content_length} exceeds 50MB limit")
                    return False

                size = 0
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        size += len(chunk)
                        if size > MAX_FILE_SIZE:
                            logger.warning(f"Skipping {url} — exceeded 50MB during download")
                            return False
                        f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def get_extension(url: str) -> str:
    path = url.split("?")[0]  # strip query params
    return os.path.splitext(path)[-1].lower()

async def process_media_url(url: str) -> Optional[str]:
    """
    Download a media file, detect type, run OCR or Whisper.
    Returns extracted text or None.
    """
    ext = get_extension(url)

    with tempfile.TemporaryDirectory() as tmpdir:
        dest_path = os.path.join(tmpdir, f"media{ext}")

        downloaded = await download_file(url, dest_path)
        if not downloaded:
            return None

        if ext in IMAGE_EXTENSIONS:
            logger.info(f"Running OCR on image: {url}")
            return await extract_text_from_image(dest_path)

        elif ext in AUDIO_EXTENSIONS or ext in VIDEO_EXTENSIONS:
            logger.info(f"Running Whisper on audio/video: {url}")
            return await transcribe_audio(dest_path)

        else:
            logger.warning(f"Unsupported media type {ext} for {url}, skipping")
            return None

async def process_media_urls(media_urls: list[str]) ->