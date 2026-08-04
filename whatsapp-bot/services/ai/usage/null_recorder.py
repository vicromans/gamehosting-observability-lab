from services.ai.usage.base import AIUsageRecord, AIUsageRecorder


class NullAIUsageRecorder(AIUsageRecorder):
    """Recorder that intentionally discards every usage record."""

    def record(self, usage: AIUsageRecord) -> None:
        return None
