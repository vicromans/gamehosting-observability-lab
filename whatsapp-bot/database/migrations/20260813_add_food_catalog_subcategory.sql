ALTER TABLE food_catalog_items
    ADD COLUMN IF NOT EXISTS subcategory VARCHAR(80) NULL
    AFTER category;

CREATE INDEX IF NOT EXISTS idx_food_catalog_business_subcategory
    ON food_catalog_items (
        business_id,
        subcategory
    );
