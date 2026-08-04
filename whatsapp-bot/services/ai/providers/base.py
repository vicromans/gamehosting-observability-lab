from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AIMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        supported_roles = {"system", "user", "assistant", "tool"}

        if self.role not in supported_roles:
            raise ValueError(
                f"Unsupported message role: {self.role!r}. "
                f"Supported roles: {', '.join(sorted(supported_roles))}."
            )

        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Message content cannot be empty.")


@dataclass(frozen=True)
class AIChatRequest:
    messages: List[AIMessage]
    tenant_id: Optional[int] = None
    conversation_id: Optional[int] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("At least one AI message is required.")

        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2.")

        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero.")


@dataclass(frozen=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise ValueError("Token usage values cannot be negative.")


@dataclass(frozen=True)
class AIChatResponse:
    content: str
    provider: str
    model: str
    usage: AIUsage = field(default_factory=AIUsage)
    request_id: Optional[str] = None
    raw_response: Optional[Any] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("AI response content cannot be empty.")

        if not self.provider.strip():
            raise ValueError("AI response provider cannot be empty.")

        if not self.model.strip():
            raise ValueError("AI response model cannot be empty.")


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable provider identifier."""

    @abstractmethod
    def chat(self, request: AIChatRequest) -> AIChatResponse:
        """Generate a response for a provider-independent chat request."""
