CREATE TABLE IF NOT EXISTS daily_menus (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,
    menu_date DATE NOT NULL,
    title VARCHAR(180) NULL,
    intro_text TEXT NULL,
    image_url VARCHAR(500) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    published_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_daily_menus_business_date (
        business_id,
        menu_date
    ),
    KEY idx_daily_menus_business_status (
        business_id,
        status
    ),

    CONSTRAINT fk_daily_menus_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS daily_menu_items (
    id INT NOT NULL AUTO_INCREMENT,
    daily_menu_id INT NOT NULL,
    item_name VARCHAR(180) NOT NULL,
    category VARCHAR(80) NULL,
    description TEXT NULL,
    price DECIMAL(10,2) NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MXN',
    available TINYINT(1) NOT NULL DEFAULT 1,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_daily_menu_items_menu (
        daily_menu_id
    ),
    KEY idx_daily_menu_items_available (
        daily_menu_id,
        available
    ),

    CONSTRAINT fk_daily_menu_items_menu
        FOREIGN KEY (daily_menu_id)
        REFERENCES daily_menus(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
