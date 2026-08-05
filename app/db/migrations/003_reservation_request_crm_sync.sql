ALTER TABLE reservation_requests
    ADD COLUMN IF NOT EXISTS crm_request_id INTEGER UNIQUE;

CREATE INDEX IF NOT EXISTS reservation_requests_crm_request_id_idx
    ON reservation_requests (crm_request_id);
