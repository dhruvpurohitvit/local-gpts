"""
Central structured logger for Sovereign AI Workbench.
Logs every routing decision, model call, RAG hit, sandbox execution, and error.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime

# ==============================================================
# PATHS
# ==============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "workbench.log")

os.makedirs(LOG_DIR, exist_ok=True)


# ==============================================================
# COLOR FORMATTER (console only)
# ==============================================================

class ColorFormatter(logging.Formatter):

    COLORS = {
        "DEBUG":    "\033[36m",   # Cyan
        "INFO":     "\033[32m",   # Green
        "WARNING":  "\033[33m",   # Yellow
        "ERROR":    "\033[31m",   # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


# ==============================================================
# BUILD LOGGER
# ==============================================================

def _build_logger(name: str = "workbench") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ----------------------------------------------------------
    # File handler — rotating, 10 MB max, keep 5 files
    # ----------------------------------------------------------
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # ----------------------------------------------------------
    # Console handler — colored
    # ----------------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    color_formatter = ColorFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(color_formatter)
    logger.addHandler(console_handler)

    return logger


# ==============================================================
# GLOBAL LOGGER
# ==============================================================

log = _build_logger("workbench")


# ==============================================================
# HELPER: get child logger for a module
# ==============================================================

def get_logger(module_name: str) -> logging.Logger:
    """Get a child logger scoped to a module."""
    return logging.getLogger(f"workbench.{module_name}")
