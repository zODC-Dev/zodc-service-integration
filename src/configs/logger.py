import logging
import sys

from loguru import logger

# Configure logger
logger.remove()  # Remove the default handler
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
)
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)

# Disable all SQLAlchemy logging except ERROR
for name in logging.root.manager.loggerDict.keys():
    if name.startswith("sqlalchemy"):
        sql_logger = logging.getLogger(name)
        sql_logger.setLevel(logging.ERROR)
        sql_logger.handlers.clear()  # Xóa toàn bộ handlers để ngăn log bị in ra

# Optional: Chặn SQLAlchemy log lan truyền
logging.getLogger("sqlalchemy").propagate = False
logging.disable(logging.WARNING)


# Export the logger
log = logger
