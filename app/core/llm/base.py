"""Common interface every model provider implements.

A provider wraps one backend's specific HTTP API behind the same three
operations the rest of the app calls through LLMClient: listing models,
chat completion, and (where supported) embeddings.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


@dataclass
class ProviderModel:
    id: str
    display_name: str = ""
    # HuggingFace-specific: True when the repo owner requires clicking
    # through a license/access agreement on the Hub before it can be used.
    # Always False for providers with no such concept.
    gated: bool = False

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = self.id


class ProviderError(RuntimeError):
    """Raised when a provider call fails (bad key, network error, bad request, ...)."""


class LLMProvider(ABC):
    id: str = ""
    display_name: str = ""
    requires_api_key: bool = True
    supports_embeddings: bool = False

    @abstractmethod
    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        ...

    @abstractmethod
    def chat(
        self,
        model: str,
        prompt: str,
        system: str,
        temperature: float,
        api_key: str,
        extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """`on_token`, if given, is called with each incremental chunk of
        text as it's generated. Only providers that actually stream
        (currently the two Ollama providers) call it more than once;
        others may ignore it or call it once with the full response."""
        ...

    def embed(self, model: str, text: str, api_key: str, extra: dict) -> list[float]:
        raise ProviderError(f"{self.display_name} does not support embeddings.")
