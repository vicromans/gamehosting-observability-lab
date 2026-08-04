from typing import Any, Optional

from services.ai.providers.base import (
    AIChatRequest,
    AIChatResponse,
    AIProvider,
)


class GeminiProviderError(RuntimeError):
    """Raised when the Gemini provider cannot complete a request."""


class GeminiProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: Optional[Any] = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key cannot be empty.")

        if not model or not model.strip():
            raise ValueError("Gemini model cannot be empty.")

        self._api_key = api_key.strip()
        self._model = model.strip()
        self._client = client

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def chat(self, request: AIChatRequest) -> AIChatResponse:
        if self._client is None:
            raise GeminiProviderError(
                "Gemini client has not been initialized yet."
            )

        raise NotImplementedError(
            "Gemini chat integration is not enabled yet."
        )
