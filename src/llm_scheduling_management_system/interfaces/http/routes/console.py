from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from llm_scheduling_management_system.interfaces.http.console_page import HTML

router = APIRouter(tags=["console"])


@router.get("/console", response_class=HTMLResponse)
def get_console() -> HTMLResponse:
    return HTMLResponse(HTML)
