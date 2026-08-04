from database.connection import get_db_connection
from services.ai.usage.base import AIUsageRecord, AIUsageRecorder


class MariaDBAIUsageRecorder(AIUsageRecorder):
    """Persist AI usage records in the ai_usage_logs table."""

    def record(self, usage: AIUsageRecord) -> None:
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_usage_logs (
                        tenant_id,
                        conversation_id,
                        provider,
                        model,
                        request_id,
                        status,
                        latency_ms,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        estimated_cost_usd,
                        error_message
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        usage.tenant_id,
                        usage.conversation_id,
                        usage.provider,
                        usage.model,
                        usage.request_id,
                        usage.status,
                        usage.latency_ms,
                        usage.input_tokens,
                        usage.output_tokens,
                        usage.total_tokens,
                        usage.estimated_cost_usd,
                        usage.error_message,
                    ),
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
