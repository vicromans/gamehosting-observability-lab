ALTER TABLE food_catalog_items
    CHANGE COLUMN default_price individual_price
        DECIMAL(10,2) DEFAULT NULL,

    ADD COLUMN pricing_mode VARCHAR(30)
        NOT NULL DEFAULT 'included'
        AFTER description,

    ADD COLUMN surcharge_amount DECIMAL(10,2)
        DEFAULT NULL
        AFTER pricing_mode,

    ADD KEY idx_food_catalog_pricing_mode (
        business_id,
        pricing_mode
    );
