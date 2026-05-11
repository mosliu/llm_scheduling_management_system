import uvicorn

from llm_scheduling_management_system.bootstrap import ensure_local_database


if __name__ == "__main__":
    ensure_local_database()
    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
