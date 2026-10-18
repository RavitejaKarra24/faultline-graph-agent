import logging


def configure_logging():
    # Uvicorn's CLI does not configure the root logger. Ensure graph-tool audit
    # records are visible with either supported entrypoint, without double handlers.
    logger = logging.getLogger("faultline_backend")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def main():
    import uvicorn

    from .config import Settings

    configure_logging()
    settings = Settings()
    uvicorn.run("faultline_backend.app:app", host=settings.host, port=settings.port)
