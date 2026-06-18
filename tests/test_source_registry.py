from llm_scheduling_management_system.source_registry import SourceRegistry


def test_source_registry_infers_cn_region_for_unregistered_cn_domains():
    registry = SourceRegistry()

    media_info = registry.lookup("www.example.cn")
    government_info = registry.lookup("www.gov.cn")

    assert media_info["region_hint"] == "cn"
    assert media_info["language"] == "zh"
    assert media_info["official"] is False
    assert government_info["region_hint"] == "cn"
    assert government_info["publisher_type"] == "government"
    assert government_info["official"] is True
