import logging
from datetime import datetime
from pathlib import Path


TRACE_LEVEL = 5
LOG_DIRECTORY = Path("files") / "logs"
logging.addLevelName(TRACE_LEVEL, "TRACE")


def build_log_path(
    workbook_path: str | Path,
    timestamp: datetime | None = None,
) -> Path:
    workbook_path = Path(workbook_path)
    timestamp = timestamp or datetime.now()
    timestamp_text = timestamp.strftime("%Y-%m-%d-%H-%M-%S")

    return LOG_DIRECTORY / f"{workbook_path.stem}_{timestamp_text}.log"


def setup_logging(workbook_path: str | Path) -> Path:
    log_path = build_log_path(workbook_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.disable(logging.NOTSET)

    file_handler = logging.FileHandler(
        log_path,
        mode="w",
        encoding="utf-8",
    )
    file_handler.setLevel(TRACE_LEVEL)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
    ))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(TRACE_LEVEL)
    root_logger.addHandler(file_handler)

    return log_path


def trace(message: str, *args) -> None:
    logging.log(TRACE_LEVEL, message, *args)
