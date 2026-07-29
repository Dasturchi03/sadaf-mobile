CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE,
    phone_number VARCHAR(32) UNIQUE,
    password_hash VARCHAR(255),
    crm_user_id INTEGER UNIQUE,
    crm_client_id INTEGER UNIQUE,
    first_name VARCHAR(80),
    last_name VARCHAR(80),
    father_name VARCHAR(80),
    birthdate DATE,
    gender VARCHAR(20),
    citizenship VARCHAR(100),
    address VARCHAR(255),
    telegram VARCHAR(80),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS users_crm_client_id_idx ON users (crm_client_id);
CREATE INDEX IF NOT EXISTS users_phone_number_idx ON users (phone_number);

CREATE TABLE IF NOT EXISTS otp_codes (
    id BIGSERIAL PRIMARY KEY,
    phone_number VARCHAR(32) NOT NULL,
    purpose VARCHAR(32) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    attempts_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS otp_codes_lookup_idx
    ON otp_codes (phone_number, purpose, expires_at DESC);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_devices (
    device_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(512) NOT NULL UNIQUE,
    platform VARCHAR(32) NOT NULL DEFAULT 'unknown',
    device_uid VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS notification_devices_user_idx
    ON notification_devices (user_id, is_active);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    crm_notification_id INTEGER UNIQUE,
    crm_reservation_id INTEGER,
    notification_type VARCHAR(64) NOT NULL DEFAULT 'general',
    notification_message VARCHAR(255),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS notifications_user_created_idx
    ON notifications (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS notifications_user_unread_idx
    ON notifications (user_id, is_read);

CREATE TABLE IF NOT EXISTS reservation_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    crm_client_id INTEGER,
    crm_doctor_id INTEGER NOT NULL,
    crm_work_id INTEGER NOT NULL,
    crm_reservation_id INTEGER,
    flutter_reservation_id VARCHAR(255) UNIQUE,
    doctor_name VARCHAR(255),
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    note VARCHAR(255),
    reservation_date DATE NOT NULL,
    reservation_time TIME NOT NULL,
    slot_minutes INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reservation_requests_user_created_idx
    ON reservation_requests (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS reservation_requests_doctor_slot_idx
    ON reservation_requests (crm_doctor_id, reservation_date, reservation_time, status);

CREATE TABLE IF NOT EXISTS referral_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(64) NOT NULL UNIQUE,
    code_type VARCHAR(32) NOT NULL DEFAULT 'user',
    bonus_amount NUMERIC(14, 2) NOT NULL DEFAULT 25000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS referral_applications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referral_code_id BIGINT NOT NULL REFERENCES referral_codes(id),
    referrer_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS cashback_entries (
    entry_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_type VARCHAR(32) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    balance_after NUMERIC(14, 2) NOT NULL,
    note VARCHAR(255),
    related_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    crm_transaction_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cashback_entries_user_created_idx
    ON cashback_entries (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS partner_inquiries (
    inquiry_id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(254),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vacancy_applications (
    application_id BIGSERIAL PRIMARY KEY,
    crm_vacancy_id INTEGER,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(254),
    address VARCHAR(255),
    birth_date DATE,
    gender VARCHAR(20),
    marital_status VARCHAR(20),
    message TEXT,
    resume_file_path VARCHAR(512),
    status VARCHAR(20) NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mobile_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100),
    aggregate_id VARCHAR(100),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mobile_events_unprocessed_idx
    ON mobile_events (processed_at, created_at);
