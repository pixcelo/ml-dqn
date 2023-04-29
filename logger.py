import os
from loguru import logger

class Logger:
    def __init__(self, log_name, log_level="INFO"):
        logger.remove()
        logger.add(
            f"log/{log_name}.log",
            level="INFO",
            format="{time} - {name} : [{level}] {message}",
            rotation="10 MB"
        )

        # Create log folder if it doesn't exist
        if not os.path.exists("log"):
            os.makedirs("log")

    def __call__(self):
        return logger