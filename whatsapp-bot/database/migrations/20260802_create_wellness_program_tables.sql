CREATE TABLE IF NOT EXISTS wellness_programs (
    id INT NOT NULL AUTO_INCREMENT,
    business_id INT NOT NULL,

    title VARCHAR(180) NOT NULL,
    program_type VARCHAR(50) NOT NULL,
    description TEXT NULL,

    delivery_mode VARCHAR(30) NOT NULL DEFAULT 'presential',
    location_name VARCHAR(180) NULL,
    location_address TEXT NULL,
    online_platform VARCHAR(80) NULL,
    online_url VARCHAR(500) NULL,

    is_free TINYINT(1) NOT NULL DEFAULT 0,
    price DECIMAL(10,2) NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MXN',

    capacity INT NULL,
    registration_status VARCHAR(30) NOT NULL DEFAULT 'open',
    registration_deadline DATETIME NULL,

    whatsapp_group_url VARCHAR(500) NULL,
    image_url VARCHAR(500) NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'draft',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_wellness_programs_business_status (
        business_id,
        status
    ),

    KEY idx_wellness_programs_business_type (
        business_id,
        program_type
    ),

    KEY idx_wellness_programs_registration (
        business_id,
        registration_status
    ),

    CONSTRAINT fk_wellness_programs_business
        FOREIGN KEY (business_id)
        REFERENCES businesses(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS wellness_program_sessions (
    id INT NOT NULL AUTO_INCREMENT,
    program_id INT NOT NULL,

    session_number INT NOT NULL DEFAULT 1,
    session_title VARCHAR(180) NULL,

    session_date DATE NOT NULL,
    start_time TIME NULL,
    end_time TIME NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_wellness_sessions_program_date (
        program_id,
        session_date
    ),

    CONSTRAINT fk_wellness_sessions_program
        FOREIGN KEY (program_id)
        REFERENCES wellness_programs(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
