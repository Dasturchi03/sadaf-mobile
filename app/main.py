import logging
from logging.handlers import TimedRotatingFileHandler
from logging.config import dictConfig
from uvicorn.config import LOGGING_CONFIG
from app.core import app


LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
LOGGING_CONFIG["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
LOGGING_CONFIG["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(client_addr)s - \"%(request_line)s\" %(status_code)s"
LOGGING_CONFIG["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
dictConfig(LOGGING_CONFIG)
formatter = logging.Formatter(u'[%(asctime)s] - %(filename)s:%(lineno)d #%(levelname)-8s  - %(name)s - %(message)s')
handler = TimedRotatingFileHandler('logs/log.log', when="midnight", interval=1, encoding='utf8')
handler.suffix = "%Y-%m-%d_%H-%M-%S"
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


from app.api import mobile
from app.api.auth.routes.auth import router as auth_router
from app.utils.i18n import SUPPORTED_LANGUAGES


def include_multilingual_router(router):
    app.include_router(router)
    for language in SUPPORTED_LANGUAGES:
        app.include_router(router, prefix=f"/{language}")


include_multilingual_router(auth_router)
include_multilingual_router(mobile.router)
