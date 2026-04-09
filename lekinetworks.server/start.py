import logging
import logging.handlers
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_project_root = Path(__file__).resolve().parent
log_dir = Path(os.environ.get("LOG_DIR", _project_root / "logs"))
log_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.handlers.RotatingFileHandler(
    log_dir / "server.log",
    maxBytes=2 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logging.getLogger().addHandler(file_handler)

from lekivpn.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
