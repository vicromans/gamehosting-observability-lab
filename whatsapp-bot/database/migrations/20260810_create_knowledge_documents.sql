CREATE TABLE IF NOT EXISTS knowledge_documents (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,

    title VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) DEFAULT NULL,
    document_type VARCHAR(50) DEFAULT NULL,
    storage_path VARCHAR(500) DEFAULT NULL,

    source_type VARCHAR(50) NOT NULL DEFAULT 'upload',

    status ENUM(
        'pending',
        'approved',
        'conflict',
        'archived'
    ) NOT NULL DEFAULT 'pending',

    notes TEXT DEFAULT NULL,

    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_knowledge_documents_business (
        business_id
    ),

    KEY idx_knowledge_documents_business_status (
        business_id,
        status
    ),

    CONSTRAINT fk_knowledge_documents_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_uca1400_ai_ci;
