BEGIN;

DO $$
BEGIN
    IF current_database() <> 'sadaf_mobile_db' THEN
        RAISE EXCEPTION 'Refusing to seed mock data into database "%". Expected "sadaf_mobile_db".', current_database();
    END IF;
END
$$;

CREATE TEMP TABLE _mock_mobile_user_ids (
    user_key TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL
) ON COMMIT DROP;

CREATE TEMP TABLE _old_mock_mobile_user_ids AS
SELECT id
FROM users
WHERE phone_number IN ('+998990011122', '+998990011123', '+998990011124')
   OR username IN ('mock.ulugbek', 'mock.madina', 'mock.dilshod')
   OR crm_client_id = 990001;

DELETE FROM mobile_events
WHERE aggregate_id LIKE 'mock-%'
   OR payload::text LIKE '%mock.ulugbek%'
   OR payload::text LIKE '%+99899001112%';

DELETE FROM referral_applications
WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids)
   OR referrer_user_id IN (SELECT id FROM _old_mock_mobile_user_ids)
   OR referral_code_id IN (
        SELECT id
        FROM referral_codes
        WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids)
           OR code LIKE 'SADAF-MOCK-%'
   );

DELETE FROM cashback_entries
WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids)
   OR related_user_id IN (SELECT id FROM _old_mock_mobile_user_ids);

DELETE FROM refresh_tokens WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids);
DELETE FROM notification_devices WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids);
DELETE FROM notifications WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids);
DELETE FROM reservation_requests WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids);
DELETE FROM user_contacts
WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids)
   OR phone_number IN ('+998990011122', '+998990011123', '+998990011124')
   OR crm_client_id = 990001;
DELETE FROM referral_codes
WHERE user_id IN (SELECT id FROM _old_mock_mobile_user_ids)
   OR code LIKE 'SADAF-MOCK-%';
DELETE FROM otp_codes WHERE phone_number IN ('+998990011122', '+998990011123', '+998990011124');
DELETE FROM users WHERE id IN (SELECT id FROM _old_mock_mobile_user_ids);

DELETE FROM partner_inquiries WHERE email LIKE '%@mock.sadaf.local';
DELETE FROM vacancy_applications WHERE email LIKE '%@mock.sadaf.local';

WITH inserted AS (
    INSERT INTO users (
        username, phone_number, crm_client_id, first_name, last_name, father_name, birthdate,
        gender, citizenship, address, telegram, is_active, is_verified, last_login_at
    )
    VALUES (
        'mock.ulugbek', '+998990011122', 990001, 'Ulugbek', 'Shermetov', 'Javlonbek ogli',
        '2003-04-13', 'male', 'UZ', 'Tashkent, Yunusabad tumani', '@Dasturchi_03',
        TRUE, TRUE, now() - interval '35 minutes'
    )
    RETURNING id
)
INSERT INTO _mock_mobile_user_ids(user_key, user_id)
SELECT 'main', id FROM inserted;

WITH inserted AS (
    INSERT INTO users (
        username, phone_number, first_name, last_name, father_name, birthdate,
        gender, citizenship, address, telegram, is_active, is_verified, last_login_at
    )
    VALUES (
        'mock.madina', '+998990011123', 'Madina', 'Karimova', 'Anvar qizi',
        '1998-09-21', 'female', 'UZ', 'Tashkent, Chilonzor tumani', '@madina_mock',
        TRUE, TRUE, now() - interval '2 days'
    )
    RETURNING id
)
INSERT INTO _mock_mobile_user_ids(user_key, user_id)
SELECT 'friend', id FROM inserted;

WITH inserted AS (
    INSERT INTO users (
        username, phone_number, first_name, last_name, father_name, birthdate,
        gender, citizenship, address, telegram, is_active, is_verified
    )
    VALUES (
        'mock.dilshod', '+998990011124', 'Dilshod', 'Tursunov', 'Akmal ogli',
        '1995-02-06', 'male', 'UZ', 'Tashkent, Mirobod tumani', '@dilshod_mock',
        FALSE, FALSE
    )
    RETURNING id
)
INSERT INTO _mock_mobile_user_ids(user_key, user_id)
SELECT 'pending', id FROM inserted;

INSERT INTO otp_codes(phone_number, purpose, code_hash, max_attempts, expires_at)
VALUES (
    '+998990011122',
    'login',
    '$2b$12$Fu6Gexee87CcMoYCWMXy5ua3lEaVNB9MWTA.h31PR22xxRScjDbZS',
    5,
    now() + interval '7 days'
);

INSERT INTO referral_codes(user_id, code, code_type, bonus_amount, is_active)
SELECT user_id, 'SADAF-MOCK-ULUGBEK', 'user', 25000, TRUE
FROM _mock_mobile_user_ids
WHERE user_key = 'main';

INSERT INTO referral_codes(user_id, code, code_type, bonus_amount, is_active)
SELECT user_id, 'SADAF-MOCK-MADINA', 'user', 25000, TRUE
FROM _mock_mobile_user_ids
WHERE user_key = 'friend';

INSERT INTO referral_applications(user_id, referral_code_id, referrer_user_id)
SELECT friend.user_id, code.id, main.user_id
FROM _mock_mobile_user_ids AS main
JOIN _mock_mobile_user_ids AS friend ON friend.user_key = 'friend'
JOIN referral_codes AS code ON code.user_id = main.user_id AND code.code = 'SADAF-MOCK-ULUGBEK'
WHERE main.user_key = 'main';

INSERT INTO cashback_entries(user_id, entry_type, amount, balance_after, note, related_user_id, created_at)
SELECT user_id, 'service_cashback', 125000, 125000, 'Ortodontiya xizmatidan cashback', NULL, now() - interval '14 days'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO user_contacts(user_id, phone_number, crm_client_id, source, last_otp_purpose, last_seen_at, created_at, updated_at)
SELECT user_id, '+998990011122', 990001, 'mock_seed', 'login', now(), now(), now()
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO user_contacts(user_id, phone_number, crm_client_id, source, last_otp_purpose, last_seen_at, created_at, updated_at)
SELECT user_id, '+998990011123', NULL, 'mock_seed', 'login', now() - interval '2 days', now() - interval '2 days', now() - interval '2 days'
FROM _mock_mobile_user_ids WHERE user_key = 'friend';

INSERT INTO cashback_entries(user_id, entry_type, amount, balance_after, note, related_user_id, created_at)
SELECT main.user_id, 'referral_bonus', 25000, 150000, 'Referral bonus', friend.user_id, now() - interval '5 days'
FROM _mock_mobile_user_ids AS main
JOIN _mock_mobile_user_ids AS friend ON friend.user_key = 'friend'
WHERE main.user_key = 'main';

INSERT INTO cashback_entries(user_id, entry_type, amount, balance_after, note, related_user_id, created_at)
SELECT user_id, 'manual_adjustment', -30000, 120000, 'Cashback ishlatildi', NULL, now() - interval '1 day'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO notification_devices(user_id, token, platform, device_uid, is_active, last_seen_at)
SELECT user_id, 'mock-fcm-token-ulugbek-android', 'android', 'mock-pixel-8', TRUE, now() - interval '10 minutes'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO notifications(user_id, crm_reservation_id, notification_type, notification_message, payload, is_read, created_at)
SELECT user_id, 990001, 'reservation',
       'Ertangi qabulingiz 10:30 ga belgilangan',
       jsonb_build_object(
           'title', 'Qabul eslatmasi',
           'reservation', jsonb_build_object(
               'reservation_id', 990001,
               'doctor_name', 'Bekzod Rahimov',
               'date', to_char(current_date + 1, 'DD-MM-YYYY'),
               'time', '10:30'
           )
       ),
       FALSE, now() - interval '20 minutes'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO notifications(user_id, crm_reservation_id, notification_type, notification_message, payload, is_read, created_at)
SELECT user_id, NULL, 'cashback',
       'Referral uchun 25 000 som cashback hisoblandi',
       jsonb_build_object('amount', 25000, 'balance_after', 150000, 'currency', 'UZS'),
       FALSE, now() - interval '5 days'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO notifications(user_id, crm_reservation_id, notification_type, notification_message, payload, is_read, created_at)
SELECT user_id, NULL, 'general',
       'Sadaf Dental mobil ilovasiga xush kelibsiz',
       jsonb_build_object('screen', 'dashboard'),
       TRUE, now() - interval '12 days'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO reservation_requests(
    user_id, crm_client_id, crm_doctor_id, crm_work_id, crm_reservation_id,
    flutter_reservation_id, doctor_name, status, note, reservation_date, reservation_time, slot_minutes,
    created_at, updated_at
)
SELECT user_id, 990001, 990001, 990001, 990001,
       'mock-upcoming-approved', 'Bekzod Rahimov', 'approved',
       'Mock: ertangi tasdiqlangan qabul',
       current_date + 1, '10:30'::time, 60,
       now() - interval '2 days', now() - interval '30 minutes'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO reservation_requests(
    user_id, crm_client_id, crm_doctor_id, crm_work_id, crm_reservation_id,
    flutter_reservation_id, doctor_name, status, note, reservation_date, reservation_time, slot_minutes,
    created_at, updated_at
)
SELECT user_id, 990001, 990002, 990002, NULL,
       'mock-draft-consultation', 'Dilnoza Kadirova', 'draft',
       'Mock: klinika tasdigini kutmoqda',
       current_date + 3, '15:00'::time, 45,
       now() - interval '6 hours', now() - interval '6 hours'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO reservation_requests(
    user_id, crm_client_id, crm_doctor_id, crm_work_id, crm_reservation_id,
    flutter_reservation_id, doctor_name, status, note, reservation_date, reservation_time, slot_minutes,
    created_at, updated_at
)
SELECT user_id, 990001, 990002, 990003, 990002,
       'mock-past-cancelled', 'Dilnoza Kadirova', 'cancelled_by_patient',
       'Mock: mijoz tomonidan bekor qilingan',
       current_date - 9, '09:00'::time, 30,
       now() - interval '12 days', now() - interval '9 days'
FROM _mock_mobile_user_ids WHERE user_key = 'main';

INSERT INTO partner_inquiries(full_name, phone, email, message, created_at, updated_at)
VALUES (
    'Mock Partner Clinic',
    '+998990022200',
    'partner@mock.sadaf.local',
    'Hamkorlik va korporativ stomatologiya xizmatlari boyicha murojaat.',
    now() - interval '4 days',
    now() - interval '4 days'
);

INSERT INTO vacancy_applications(
    crm_vacancy_id, first_name, last_name, middle_name, phone, email, address,
    birth_date, gender, marital_status, message, resume_file_path, status, created_at, updated_at
)
VALUES (
    1, 'Mock', 'Applicant', 'Testovich', '+998990033300',
    'applicant@mock.sadaf.local', 'Tashkent, Shayxontohur tumani',
    '1997-11-18', 'male', 'single',
    'Mobil backend seed orqali yaratilgan test ariza.',
    'uploads/vacancies/mock-applicant-resume.pdf',
    'new',
    now() - interval '3 days',
    now() - interval '3 days'
);

INSERT INTO mobile_events(event_type, aggregate_type, aggregate_id, payload, created_at)
SELECT 'mock.seed.created', 'user', 'mock-main-user',
       jsonb_build_object(
           'username', 'mock.ulugbek',
           'phone_number', '+998990011122',
           'otp_code', '111111',
           'note', 'Local mock data for mobile app testing'
       ),
       now()
FROM _mock_mobile_user_ids WHERE user_key = 'main';

COMMIT;
