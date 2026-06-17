from pathlib import Path

from llm_scheduling_management_system.interfaces.http.briefing_page import HTML


def main() -> None:
    """导出单文件用户侧研判页 HTML。"""
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "docs" / "briefing-standalone.html"
    output_path.write_text(HTML, encoding="utf-8")
    print(f"Exported standalone briefing page to {output_path}")


if __name__ == "__main__":
    main()
