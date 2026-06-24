from pathlib import Path
import sys

import uvicorn

from llm_scheduling_management_system.bootstrap import ensure_local_database


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    ensure_local_database()
    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
