from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import Settings


def configure_logging(settings: Settings) -> None:
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)
