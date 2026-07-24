ALTER TABLE food_catalog_items
    ADD COLUMN included_in_meal TINYINT(1)
        NOT NULL DEFAULT 1
        AFTER description,

    ADD COLUMN has_surcharge TINYINT(1)
        NOT NULL DEFAULT 0
        AFTER included_in_meal,

    ADD COLUMN available_individually TINYINT(1)
        NOT NULL DEFAULT 0
        AFTER surcharge_amount;

UPDATE food_catalog_items
SET
    included_in_meal = CASE
        WHEN pricing_mode IN ('included', 'surcharge') THEN 1
        ELSE 0
    END,

    has_surcharge = CASE
        WHEN pricing_mode = 'surcharge' THEN 1
        ELSE 0
    END,

    available_individually = CASE
        WHEN pricing_mode = 'individual' THEN 1
        ELSE 0
    END;

ALTER TABLE food_catalog_items
    DROP KEY idx_food_catalog_pricing_mode,
    DROP COLUMN pricing_mode;
