import logging
import os
import tempfile
from pathlib import Path

import httpx

from backend.settings import settings

logger = logging.getLogger(__name__)


def download_asset(url: str, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        logger.info("Skipping existing asset: %s", destination)
        return destination.stat().st_size
    temporary_path: Path | None = None
    try:
        with httpx.stream("GET", url, timeout=settings.download_timeout_seconds, follow_redirects=True) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > settings.max_download_bytes:
                raise ValueError(f"Asset exceeds max download size: {url}")
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > settings.max_download_bytes:
                        raise ValueError(f"Asset exceeded max download size: {url}")
                    temporary.write(chunk)
        os.replace(temporary_path, destination)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    logger.info("Downloaded %s bytes to %s", size, destination)
    return size