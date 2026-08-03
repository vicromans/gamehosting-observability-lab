ALTER TABLE appointments
    ADD COLUMN session_type_id INT NULL AFTER service_name,
    ADD COLUMN duration_minutes INT NULL AFTER appointment_time,
    ADD COLUMN delivery_mode VARCHAR(30) NULL AFTER duration_minutes;

CREATE INDEX idx_appointments_business_date
    ON appointments (business_id, appointment_date, appointment_time);

CREATE INDEX idx_appointments_session_type
    ON appointments (session_type_id);
