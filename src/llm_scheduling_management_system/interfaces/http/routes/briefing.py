from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from llm_scheduling_management_system.interfaces.http.briefing_page import HTML

router = APIRouter(tags=["briefing"])


@router.get("/briefing", response_class=HTMLResponse)
def get_briefing() -> HTMLResponse:
    """获取面向非技术用户的独立研判页面。

    用途:
        返回一个独立于控制台的简化版 HTML 页面，供非技术用户直接提交研判任务、轮询进展并查看最终结果。

    用法:
        GET /briefing

    @Author: mosliu
    """
    return HTMLResponse(HTML)
