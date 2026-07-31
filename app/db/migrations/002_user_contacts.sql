CREATE TABLE IF NOT EXISTS user_contacts (
    contact_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    phone_number VARCHAR(32) NOT NULL UNIQUE,
    crm_client_id INTEGER,
    source VARCHAR(32) NOT NULL DEFAULT 'otp',
    last_otp_purpose VARCHAR(32),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS user_contacts_phone_idx ON user_contacts (phone_number);
CREATE INDEX IF NOT EXISTS user_contacts_user_idx ON user_contacts (user_id);
