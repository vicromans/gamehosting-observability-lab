CREATE TABLE IF NOT EXISTS wellness_schedule_blocks (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,
    blocked_date DATE NOT NULL,
    start_time TIME NULL,
    end_time TIME NULL,
    reason VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_wellness_blocks_business_date (
        business_id,
        blocked_date
    ),

    CONSTRAINT fk_wellness_blocks_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
);
