import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from llm_scheduling_management_system.interfaces.http.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    app = create_app()
    client = TestClient(app)
    response = client.get(f"/api/v1/tasks/{args.task_id}/bundle")
    response.raise_for_status()
    payload = response.json()

    output_path = Path(args.output) if args.output else Path("artifacts") / f"{args.task_id}.bundle.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
