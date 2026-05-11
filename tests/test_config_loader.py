from pathlib import Path

from llm_scheduling_management_system.config_loader import load_llm_config, load_search_config, resolve_config_path


def test_resolve_config_path_prefers_primary(tmp_path: Path):
    primary = tmp_path / "search.toml"
    fallback = tmp_path / "search.example.toml"
    primary.write_text("[policy]\ndefault_time_window_days = 3\n", encoding="utf-8")
    fallback.write_text("[policy]\ndefault_time_window_days = 7\n", encoding="utf-8")

    resolved = resolve_config_path(primary, fallback)

    assert resolved == primary


def test_load_search_config_from_explicit_path(tmp_path: Path):
    config_file = tmp_path / "search.toml"
    config_file.write_text(
        """
[[providers]]
name = "exa_search"
provider_type = "search_with_inline_content"
vendor = "exa"
base_url = "https://api.exa.ai"
api_key = "replace-me"
timeout_seconds = 30
enabled = true

[policy]
default_time_window_days = 5
max_results_per_provider = 25
default_search_providers = ["exa_search"]
""".strip(),
        encoding="utf-8",
    )

    config = load_search_config(config_file)

    assert config.policy.default_time_window_days == 5
    assert config.policy.default_search_providers == ["exa_search"]


def test_load_llm_config_from_explicit_path(tmp_path: Path):
    config_file = tmp_path / "llm.toml"
    config_file.write_text(
        """
[[providers]]
name = "openai_primary"
provider_type = "openai"
base_url = "https://api.openai.com/v1"
api_key = "replace-me"
timeout_seconds = 60

[[profiles]]
name = "cheap_structured_cn"
provider = "openai_primary"
model = "gpt-4.1-mini"
temperature = 0.1
max_tokens = 4000
structured_output = true
fallback_profiles = []
""".strip(),
        encoding="utf-8",
    )

    config = load_llm_config(config_file)

    assert config.providers[0].provider_type == "openai"
    assert config.profiles[0].model == "gpt-4.1-mini"
