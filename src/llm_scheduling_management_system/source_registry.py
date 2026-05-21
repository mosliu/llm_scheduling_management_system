from llm_scheduling_management_system.config_loader import load_source_registry_config


class SourceRegistry:
    """数据源注册管理器。

    用途:
        用于加载源注册表配置，并根据域名对数据源的发布者属性、区域暗示、语言以及官方身份进行检索和匹配。

    用法:
        实例化 SourceRegistry 后，调用 lookup(domain) 方法查询某域名的注册元数据。

    @Author: mosliu
    """

    def __init__(self) -> None:
        """初始化数据源注册管理器。

        用途:
            加载并解析数据源配置文件，在内存中构建以域名为键的快速索引。

        用法:
            registry = SourceRegistry()

        @Author: mosliu
        """
        self.config = load_source_registry_config()
        self._by_domain = {entry.domain: entry for entry in self.config.sources}

    def lookup(self, domain: str) -> dict:
        """根据域名检索该数据源的信息。

        用途:
            根据传入的域名查询其所属的区域提示、出版物类型、语言及官方标识。若无匹配记录，则返回包含 "unknown" 的默认属性字典。

        用法:
            info = registry.lookup("example.com")

        参数:
            domain (str): 要检索的域名。

        返回:
            dict: 包含区域、出版物类型、语言和官方标识的字典。

        @Author: mosliu
        """
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
