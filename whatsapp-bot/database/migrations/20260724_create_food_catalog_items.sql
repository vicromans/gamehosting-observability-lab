CREATE TABLE IF NOT EXISTS food_catalog_items (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,
    item_name VARCHAR(180) NOT NULL,
    category VARCHAR(80) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    default_price DECIMAL(10,2) DEFAULT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
    active TINYINT(1) NOT NULL DEFAULT 1,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_food_catalog_business_active (
        business_id,
        active
    ),

    KEY idx_food_catalog_business_category (
        business_id,
        category
    ),

    CONSTRAINT fk_food_catalog_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
);
