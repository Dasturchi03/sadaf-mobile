BEGIN;

DO $$
BEGIN
    IF current_database() <> 'sadaf_mobile_db' THEN
        RAISE EXCEPTION 'Refusing to seed mock mobile data into database "%". Expected "sadaf_mobile_db".', current_database();
    END IF;
END
$$;

\if :{?crm_client_id}
\else
\set crm_client_id 931059966
\endif

CREATE TEMP TABLE _mobile_flow_user (
    user_id BIGINT NOT NULL,
    crm_client_id INTEGER NOT NULL
) ON COMMIT DROP;

WITH mobile_ctx AS (
    SELECT COALESCE(
        (SELECT crm_client_id FROM users WHERE phone_number = '+998931059966' AND crm_client_id IS NOT NULL LIMIT 1),
        (SELECT crm_client_id FROM user_contacts WHERE phone_number = '+998931059966' AND crm_client_id IS NOT NULL LIMIT 1),
        :'crm_client_id'::integer
    ) AS crm_client_id
),
upserted_user AS (
    INSERT INTO users(
        username, phone_number, crm_client_id,
        first_name, last_name, father_name, birthdate,
        gender, citizenship, address, telegram,
        is_active, is_verified, last_login_at
    )
    SELECT
        '+998931059966', '+998931059966', crm_client_id,
        'Test', 'Mobile', 'Sadaf', '1996-05-09',
        'male', 'UZ', 'Toshkent', '@mobile_test_998931059966',
        TRUE, TRUE, now()
    FROM mobile_ctx
    ON CONFLICT (phone_number) DO UPDATE SET
        username = EXCLUDED.username,
        crm_client_id = EXCLUDED.crm_client_id,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        father_name = EXCLUDED.father_name,
        birthdate = EXCLUDED.birthdate,
        gender = EXCLUDED.gender,
        citizenship = EXCLUDED.citizenship,
        address = EXCLUDED.address,
        telegram = EXCLUDED.telegram,
        is_active = TRUE,
        is_verified = TRUE,
        updated_at = now()
    RETURNING id, crm_client_id
)
INSERT INTO _mobile_flow_user(user_id, crm_client_id)
SELECT id, crm_client_id FROM upserted_user;

INSERT INTO user_contacts(
    user_id, phone_number, crm_client_id, source,
    last_otp_purpose, last_seen_at, created_at, updated_at
)
SELECT user_id, '+998931059966', crm_client_id, 'mock_flow_seed',
       'login', now(), now(), now()
FROM _mobile_flow_user
ON CONFLICT (phone_number) DO UPDATE SET
    user_id = EXCLUDED.user_id,
    crm_client_id = EXCLUDED.crm_client_id,
    source = EXCLUDED.source,
    last_seen_at = now(),
    updated_at = now();

DO $$
DECLARE
    target_user_id BIGINT;
    target_crm_client_id INTEGER;
    existing_request_id BIGINT;
BEGIN
    SELECT user_id, crm_client_id
    INTO target_user_id, target_crm_client_id
    FROM _mobile_flow_user
    LIMIT 1;

    SELECT id
    INTO existing_request_id
    FROM reservation_requests
    WHERE user_id = target_user_id
      AND status = 'draft'
      AND reservation_date >= current_date
    ORDER BY created_at DESC
    LIMIT 1;

    IF existing_request_id IS NOT NULL THEN
        UPDATE reservation_requests
        SET crm_client_id = target_crm_client_id,
            crm_doctor_id = 931059001,
            crm_work_id = 931059001,
            crm_request_id = 931059001,
            crm_reservation_id = 931059001,
            doctor_name = 'Sarvar Turgunov',
            status = 'approved',
            note = 'Accepted existing mobile request for 998931059966',
            reservation_date = current_date + 1,
            reservation_time = '09:00'::time,
            slot_minutes = 60,
            updated_at = now()
        WHERE id = existing_request_id;
    ELSE
        INSERT INTO reservation_requests(
            user_id, crm_client_id, crm_doctor_id, crm_work_id,
            crm_request_id, crm_reservation_id, flutter_reservation_id,
            doctor_name, status, note, reservation_date, reservation_time, slot_minutes,
            created_at, updated_at
        )
        VALUES (
            target_user_id, target_crm_client_id, 931059001, 931059001,
            931059001, 931059001, 'mock-998931059966-accepted',
            'Sarvar Turgunov', 'approved',
            'Inserted accepted mobile request for 998931059966',
            current_date + 1, '09:00'::time, 60,
            now() - interval '2 hours', now()
        )
        ON CONFLICT (flutter_reservation_id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            crm_client_id = EXCLUDED.crm_client_id,
            crm_doctor_id = EXCLUDED.crm_doctor_id,
            crm_work_id = EXCLUDED.crm_work_id,
            crm_request_id = EXCLUDED.crm_request_id,
            crm_reservation_id = EXCLUDED.crm_reservation_id,
            doctor_name = EXCLUDED.doctor_name,
            status = EXCLUDED.status,
            note = EXCLUDED.note,
            reservation_date = EXCLUDED.reservation_date,
            reservation_time = EXCLUDED.reservation_time,
            slot_minutes = EXCLUDED.slot_minutes,
            updated_at = now();
    END IF;

    INSERT INTO reservation_requests(
        user_id, crm_client_id, crm_doctor_id, crm_work_id,
        crm_request_id, crm_reservation_id, flutter_reservation_id,
        doctor_name, status, note, reservation_date, reservation_time, slot_minutes,
        created_at, updated_at
    )
    VALUES (
        target_user_id, target_crm_client_id, 931059002, 931059002,
        931059002, NULL, 'mock-998931059966-draft',
        'Dinara Abdurazakova', 'draft',
        'Pending mock request for Qabul status check',
        current_date + 6, '16:00'::time, 60,
        now() - interval '20 minutes', now() - interval '20 minutes'
    )
    ON CONFLICT (flutter_reservation_id) DO UPDATE SET
        user_id = EXCLUDED.user_id,
        crm_client_id = EXCLUDED.crm_client_id,
        crm_doctor_id = EXCLUDED.crm_doctor_id,
        crm_work_id = EXCLUDED.crm_work_id,
        crm_request_id = EXCLUDED.crm_request_id,
        crm_reservation_id = NULL,
        doctor_name = EXCLUDED.doctor_name,
        status = 'draft',
        note = EXCLUDED.note,
        reservation_date = EXCLUDED.reservation_date,
        reservation_time = EXCLUDED.reservation_time,
        slot_minutes = EXCLUDED.slot_minutes,
        updated_at = now();
END
$$;

DELETE FROM notifications
WHERE user_id IN (SELECT user_id FROM _mobile_flow_user)
  AND crm_reservation_id = 931059001
  AND notification_type = 'reservation'
  AND notification_message = 'Qabul sorovingiz klinika tomonidan tasdiqlandi';

INSERT INTO notifications(
    user_id, crm_reservation_id, notification_type,
    notification_message, payload, is_read, created_at
)
SELECT user_id, 931059001, 'reservation',
       'Qabul sorovingiz klinika tomonidan tasdiqlandi',
       jsonb_build_object(
           'reservation_id', 931059001,
           'reservation_request_id', 931059001,
           'doctor_name', 'Sarvar Turgunov',
           'date', to_char(current_date + 1, 'DD-MM-YYYY'),
           'start_time', '09:00'
       ),
       FALSE, now() - interval '5 minutes'
FROM _mobile_flow_user;

INSERT INTO mobile_events(event_type, aggregate_type, aggregate_id, payload, created_at)
SELECT 'mock_flow.seeded', 'user', user_id::text,
       jsonb_build_object(
           'phone_number', '+998931059966',
           'crm_client_id', crm_client_id,
           'crm_reservations', jsonb_build_array(931059001, 931059002, 931059003)
       ),
       now()
FROM _mobile_flow_user;

SELECT 'seeded_mobile_user_id' AS key, user_id AS value FROM _mobile_flow_user;
SELECT 'seeded_mobile_crm_client_id' AS key, crm_client_id AS value FROM _mobile_flow_user;

COMMIT;
