from services.ai.usage.base import (
    AIUsageRecord,
    AIUsageRecorder,
)
from services.ai.usage.null_recorder import NullAIUsageRecorder

__all__ = [
    "AIUsageRecord",
    "AIUsageRecorder",
    "MariaDBAIUsageRecorder",
    "NullAIUsageRecorder",
]


def __getattr__(name):
    if name == "MariaDBAIUsageRecorder":
        from services.ai.usage.mariadb_recorder import (
            MariaDBAIUsageRecorder,
        )

        return MariaDBAIUsageRecorder

    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
