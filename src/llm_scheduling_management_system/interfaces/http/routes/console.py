from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from llm_scheduling_management_system.interfaces.http.console_page import HTML

router = APIRouter(tags=["console"])


@router.get("/console", response_class=HTMLResponse)
def get_console() -> HTMLResponse:
    """获取控制台 HTML 页面。

    用途:
        返回控制台的单页 Web 界面 HTML 响应。

    用法:
        GET /console

    @Author: mosliu
    """
    return HTMLResponse(HTML)
