CREATE TABLE IF NOT EXISTS business_settings (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,
    slug VARCHAR(120) NOT NULL,
    email VARCHAR(255) NULL,
    address TEXT NULL,
    timezone VARCHAR(100) NOT NULL DEFAULT 'America/Mexico_City',
    opening_time TIME NULL,
    closing_time TIME NULL,
    working_days VARCHAR(50) NULL,
    description TEXT NULL,
    founded_year SMALLINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_business_settings_business_id (business_id),
    UNIQUE KEY uq_business_settings_slug (slug),

    CONSTRAINT fk_business_settings_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
