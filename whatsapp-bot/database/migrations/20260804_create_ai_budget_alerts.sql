CREATE TABLE IF NOT EXISTS ai_budget_alerts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    tenant_id INT NOT NULL,
    alert_month DATE NOT NULL,
    level ENUM('warning', 'exceeded') NOT NULL,

    utilization_percent DECIMAL(7, 2) NOT NULL,
    spent_usd DECIMAL(18, 10) NOT NULL,
    monthly_budget_usd DECIMAL(18, 10) NOT NULL,

    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    UNIQUE KEY uq_ai_budget_alert_month_level (
        tenant_id,
        alert_month,
        level
    ),

    INDEX idx_ai_budget_alert_sent_at (sent_at),
    INDEX idx_ai_budget_alert_tenant (tenant_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
