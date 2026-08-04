CREATE TABLE IF NOT EXISTS wellness_program_registrations (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,
    program_id INT NOT NULL,
    customer_id INT NOT NULL,

    registration_status VARCHAR(30) NOT NULL DEFAULT 'registered',
    payment_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    amount_paid DECIMAL(10,2) NULL,
    notes TEXT NULL,

    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    UNIQUE KEY uq_wellness_program_customer (
        program_id,
        customer_id
    ),

    KEY idx_wellness_registration_business (
        business_id
    ),

    KEY idx_wellness_registration_program (
        program_id
    ),

    KEY idx_wellness_registration_customer (
        customer_id
    ),

    CONSTRAINT fk_wellness_registration_program
        FOREIGN KEY (program_id)
        REFERENCES wellness_programs(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_wellness_registration_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
        ON DELETE RESTRICT
);
