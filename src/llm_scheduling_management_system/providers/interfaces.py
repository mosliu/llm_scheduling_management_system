from __future__ import annotations

from abc import ABC, abstractmethod

from llm_scheduling_management_system.providers.types import FetchDocument, SearchResultBundle


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, *, limit: int = 10) -> SearchResultBundle:
        raise NotImplementedError


class FetchProvider(ABC):
    @abstractmethod
    def fetch(self, url: str) -> FetchDocument:
        raise NotImplementedError


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
