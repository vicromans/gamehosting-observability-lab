CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    tenant_id INT NULL,
    conversation_id INT NULL,

    provider VARCHAR(50) NOT NULL,
    model VARCHAR(150) NOT NULL,
    request_id VARCHAR(255) NULL,

    status ENUM('success', 'error') NOT NULL,

    latency_ms INT UNSIGNED NOT NULL DEFAULT 0,

    input_tokens INT UNSIGNED NOT NULL DEFAULT 0,
    output_tokens INT UNSIGNED NOT NULL DEFAULT 0,
    total_tokens INT UNSIGNED NOT NULL DEFAULT 0,

    estimated_cost_usd DECIMAL(18, 10) NOT NULL DEFAULT 0.0000000000,

    error_message TEXT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    INDEX idx_ai_usage_created_at (created_at),
    INDEX idx_ai_usage_tenant_created (tenant_id, created_at),
    INDEX idx_ai_usage_provider_model (provider, model),
    INDEX idx_ai_usage_status_created (status, created_at),
    INDEX idx_ai_usage_request_id (request_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
