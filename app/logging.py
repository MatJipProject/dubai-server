import logging
import sys
from app.config.config import settings


def configure_logging():
    try:
        log_file_path = "app.log"
        if settings.ENVIRONMENT == "PROD":
            logging.basicConfig(
                level=logging.INFO,
                format="%(levelname)s %(asctime)s %(name)s %(pathname)s %(lineno)d %(message)s",
                handlers=[
                    logging.FileHandler(log_file_path),
                    logging.StreamHandler(sys.stdout),
                ],
            )
        else:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(levelname)s %(asctime)s %(name)s %(pathname)s %(lineno)d %(message)s",
                handlers=[logging.StreamHandler(sys.stdout)],
            )

        loggers = logging.getLogger("app")
        return loggers
    except Exception as e:
        print(f"Failed to configure logging: {e}")


logger = configure_logging()
