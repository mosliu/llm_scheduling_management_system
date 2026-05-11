from fastapi import FastAPI

from llm_scheduling_management_system.db import init_db
from llm_scheduling_management_system.interfaces.http.routes.configuration import router as configuration_router
from llm_scheduling_management_system.interfaces.http.routes.console import router as console_router
from llm_scheduling_management_system.interfaces.http.routes.provider_catalog import router as provider_catalog_router
from llm_scheduling_management_system.interfaces.http.routes.catalog import router as catalog_router
from llm_scheduling_management_system.interfaces.http.routes.inspection import router as inspection_router
from llm_scheduling_management_system.interfaces.http.routes.reports import router as reports_router
from llm_scheduling_management_system.interfaces.http.routes.system import router as system_router
from llm_scheduling_management_system.interfaces.http.routes.tasks import router as tasks_router
from llm_scheduling_management_system.logging import configure_logging, logger
from llm_scheduling_management_system.settings import settings


def create_app() -> FastAPI:
    configure_logging()
    init_db()
    logger.info("Initializing FastAPI application for {}", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(catalog_router)
    app.include_router(configuration_router)
    app.include_router(console_router)
    app.include_router(inspection_router)
    app.include_router(provider_catalog_router)
    app.include_router(reports_router)
    app.include_router(system_router)
    app.include_router(tasks_router)
    return app


app = create_app()
