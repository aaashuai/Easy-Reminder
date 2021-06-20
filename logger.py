# coding: utf-8
import datetime
import logging.config

LOG_FILE = datetime.datetime.now().strftime("%Y-%m-%d") + ".log"
LOG_PATH = "../main.log"

logging_config = {
    "version": 1,
    "incremental": False,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "class": "logging.Formatter",
            'format': '+ %(asctime)s.%(msecs)03dZ %(levelname)s <%(module)s> | %(lineno)d %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger("default")
logger.setLevel(logging.INFO)
