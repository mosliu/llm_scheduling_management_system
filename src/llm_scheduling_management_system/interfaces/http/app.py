from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_scheduling_management_system.config_loader import load_app_config
from llm_scheduling_management_system.db import init_db
from llm_scheduling_management_system.interfaces.http.routes.briefing import router as briefing_router
from llm_scheduling_management_system.interfaces.http.routes.configuration import router as configuration_router
from llm_scheduling_management_system.interfaces.http.routes.console import router as console_router
from llm_scheduling_management_system.interfaces.http.routes.provider_catalog import router as provider_catalog_router
from llm_scheduling_management_system.interfaces.http.routes.catalog import router as catalog_router
from llm_scheduling_management_system.interfaces.http.routes.inspection import router as inspection_router
from llm_scheduling_management_system.interfaces.http.routes.reports import router as reports_router
from llm_scheduling_management_system.interfaces.http.routes.system import router as system_router
from llm_scheduling_management_system.interfaces.http.routes.tasks import router as tasks_router
from llm_scheduling_management_system.logging import configure_logging, logger
from llm_scheduling_management_system.security import register_access_control
from llm_scheduling_management_system.settings import settings


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用程序实例。

    用途:
        初始化日志、数据库，并注册访问控制中间件与所有的 API 路由。

    用法:
        app = create_app()

    @Author: mosliu
    """
    configure_logging()
    init_db()
    logger.info("Initializing FastAPI application for {}", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )
    app_config = load_app_config()
    register_access_control(app)
    if app_config.api.cors.enabled:
        logger.info(
            "CORS enabled with origins={} origin_regex={}",
            app_config.api.cors.allow_origins,
            app_config.api.cors.allow_origin_regex,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_config.api.cors.allow_origins or ["*"],
            allow_origin_regex=app_config.api.cors.allow_origin_regex,
            allow_methods=app_config.api.cors.allow_methods,
            allow_headers=app_config.api.cors.allow_headers,
            expose_headers=app_config.api.cors.expose_headers,
            allow_credentials=app_config.api.cors.allow_credentials,
            max_age=app_config.api.cors.max_age,
        )

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        """系统健康检查端点。

        用途:
            提供轻量级的接口以检测应用是否正在运行。

        用法:
            GET /healthz

        @Author: mosliu
        """
        return {"status": "ok"}

    app.include_router(catalog_router)
    app.include_router(briefing_router)
    app.include_router(configuration_router)
    app.include_router(console_router)
    app.include_router(inspection_router)
    app.include_router(provider_catalog_router)
    app.include_router(reports_router)
    app.include_router(system_router)
    app.include_router(tasks_router)
    return app


app = create_app()

