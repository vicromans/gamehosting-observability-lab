ALTER TABLE business_settings
    ADD COLUMN IF NOT EXISTS ai_monthly_budget_usd
        DECIMAL(12, 4) NULL
        AFTER founded_year,
    ADD COLUMN IF NOT EXISTS ai_budget_warning_percent
        DECIMAL(5, 2) NOT NULL DEFAULT 80.00
        AFTER ai_monthly_budget_usd;
