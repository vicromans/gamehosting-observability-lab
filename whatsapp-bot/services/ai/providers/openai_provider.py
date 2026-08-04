from typing import Any, Dict, List, Optional

from services.ai.providers.base import (
    AIChatRequest,
    AIChatResponse,
    AIProvider,
    AIUsage,
)


class OpenAIProviderError(RuntimeError):
    """Raised when the OpenAI provider cannot complete a request."""


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: Optional[Any] = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("OpenAI API key cannot be empty.")

        if not model or not model.strip():
            raise ValueError("OpenAI model cannot be empty.")

        self._api_key = api_key.strip()
        self._model = model.strip()
        self._client = client

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIProviderError(
                "The OpenAI SDK is not installed. "
                "Add it to requirements.txt and rebuild the application."
            ) from exc

        self._client = OpenAI(api_key=self._api_key)
        return self._client

    @staticmethod
    def _build_input(request: AIChatRequest) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        for message in request.messages:
            role = message.role

            # Responses API uses developer instructions for application-level
            # behavior. Preserve compatibility with our provider-independent
            # "system" role by translating it here.
            if role == "system":
                role = "developer"

            if role == "tool":
                raise OpenAIProviderError(
                    "Tool messages are not supported yet. "
                    "Tool Calling will be added in a later phase."
                )

            messages.append(
                {
                    "role": role,
                    "content": message.content,
                }
            )

        return messages

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)

        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        extracted_parts: List[str] = []

        for output_item in getattr(response, "output", []) or []:
            if getattr(output_item, "type", None) != "message":
                continue

            for content_item in getattr(output_item, "content", []) or []:
                if getattr(content_item, "type", None) != "output_text":
                    continue

                text = getattr(content_item, "text", None)
                if isinstance(text, str) and text.strip():
                    extracted_parts.append(text.strip())

        return "\n".join(extracted_parts).strip()

    def chat(self, request: AIChatRequest) -> AIChatResponse:
        client = self._get_client()

        request_arguments: Dict[str, Any] = {
            "model": self._model,
            "input": self._build_input(request),
        }

        if request.temperature is not None:
            request_arguments["temperature"] = request.temperature

        if request.max_output_tokens is not None:
            request_arguments["max_output_tokens"] = request.max_output_tokens

        try:
            response = client.responses.create(**request_arguments)
        except Exception as exc:
            raise OpenAIProviderError(
                f"OpenAI request failed: {exc}"
            ) from exc

        content = self._extract_output_text(response)

        if not content:
            raise OpenAIProviderError(
                "OpenAI returned no text content."
            )

        usage = getattr(response, "usage", None)

        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(
            getattr(
                usage,
                "total_tokens",
                input_tokens + output_tokens,
            )
            or 0
        )

        return AIChatResponse(
            content=content,
            provider=self.name,
            model=str(getattr(response, "model", None) or self._model),
            usage=AIUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            request_id=getattr(response, "id", None),
            raw_response=response,
        )
