from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from typing import Any
from dataclasses import dataclass
from src.core.provider import LLMProvider, EmbedderProvider, DocumentStoreProvider
from src.core.engine import Engine


class BasicPipeline(metaclass=ABCMeta):
    def __init__(self, pipe):
        self._pipe = pipe

    @abstractmethod
    def run(self, *args, **kwargs) -> dict[str, Any]: ...


@dataclass
class PipelineComponent(Mapping):  # mapping is anything that acts like a dict
    llm_provider: LLMProvider = None
    embedder_provider: EmbedderProvider = None
    document_store_provider: DocumentStoreProvider = None
    # engine:Engine=None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self) -> int:
        return len(self.__dict__)
