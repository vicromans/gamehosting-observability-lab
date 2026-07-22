CREATE TABLE IF NOT EXISTS whatsapp_media (
    id INT NOT NULL AUTO_INCREMENT,
    message_id INT NOT NULL,
    business_id INT NOT NULL DEFAULT 1,
    phone_number VARCHAR(50) DEFAULT NULL,
    media_type VARCHAR(30) NOT NULL,
    media_id VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) DEFAULT NULL,
    caption TEXT DEFAULT NULL,
    local_path VARCHAR(500) DEFAULT NULL,
    sha256 VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_whatsapp_media_media_id (media_id),
    KEY idx_whatsapp_media_message_id (message_id),
    KEY idx_whatsapp_media_business_phone (business_id, phone_number),

    CONSTRAINT fk_whatsapp_media_message
        FOREIGN KEY (message_id)
        REFERENCES whatsapp_messages(id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_uca1400_ai_ci;
