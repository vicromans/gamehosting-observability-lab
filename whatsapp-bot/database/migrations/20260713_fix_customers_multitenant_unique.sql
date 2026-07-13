ALTER TABLE customers
    DROP INDEX phone_number,
    ADD UNIQUE KEY uq_customers_business_phone (
        business_id,
        phone_number
    ),
    ADD KEY idx_customers_business_id (
        business_id
    );
