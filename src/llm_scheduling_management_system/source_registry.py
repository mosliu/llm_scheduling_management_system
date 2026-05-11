from llm_scheduling_management_system.config_loader import load_source_registry_config


class SourceRegistry:
    def __init__(self) -> None:
        self.config = load_source_registry_config()
        self._by_domain = {entry.domain: entry for entry in self.config.sources}

    def lookup(self, domain: str) -> dict:
        entry = self._by_domain.get(domain)
        if entry is None:
            return {
                "region_hint": "unknown",
                "publisher_type": "unknown",
                "language": "unknown",
                "official": False,
            }
        return {
            "region_hint": entry.region_hint,
            "publisher_type": entry.publisher_type,
            "language": entry.language,
            "official": entry.official,
        }
