BEGIN;

DO $$
BEGIN
    IF current_database() <> 'sadaf_test_db' THEN
        RAISE EXCEPTION 'Refusing to seed mock CRM data into database "%". Expected "sadaf_test_db".', current_database();
    END IF;
END
$$;

CREATE TEMP TABLE _mobile_flow_ctx (
    client_id INTEGER NOT NULL,
    doctor_one_id INTEGER NOT NULL,
    doctor_two_id INTEGER NOT NULL,
    work_one_id INTEGER NOT NULL,
    work_two_id INTEGER NOT NULL,
    work_three_id INTEGER NOT NULL,
    reservation_one_id INTEGER NOT NULL,
    reservation_two_id INTEGER NOT NULL,
    reservation_three_id INTEGER NOT NULL,
    card_one_id INTEGER NOT NULL,
    card_two_id INTEGER NOT NULL,
    card_three_id INTEGER NOT NULL
) ON COMMIT DROP;

WITH existing_client AS (
    SELECT c.client_id
    FROM client_client c
    JOIN client_client_public_phone p ON p.client_id = c.client_id
    WHERE p.public_phone IN ('+998931059966', '998931059966')
      AND COALESCE(p.deleted, FALSE) = FALSE
      AND COALESCE(c.deleted, FALSE) = FALSE
    ORDER BY c.client_id
    LIMIT 1
),
inserted_client AS (
    INSERT INTO client_client(
        client_id, client_firstname, client_lastname, client_father_name,
        client_birthdate, client_gender, client_address, client_citizenship,
        client_telegram, client_type, client_balance, archive, deleted,
        updated_at, created_at, client_user_id, client_last_viewed_at, note,
        cashback_balance, loyalty_tier, referral_code, referred_by_id, total_spent_amount
    )
    SELECT
        931059966, 'Test', 'Mobile', 'Sadaf',
        '1996-05-09', 'Male', 'Toshkent', 'UZ',
        '@mobile_test_998931059966', 'Basic', 250000, FALSE, FALSE,
        now(), now() - interval '40 days', NULL, now(),
        'Mock flow client for mobile reservations/treatments',
        80000, 'bronze', NULL, NULL, 2450000
    WHERE NOT EXISTS (SELECT 1 FROM existing_client)
    ON CONFLICT (client_id) DO UPDATE SET
        client_firstname = EXCLUDED.client_firstname,
        client_lastname = EXCLUDED.client_lastname,
        client_father_name = EXCLUDED.client_father_name,
        client_birthdate = EXCLUDED.client_birthdate,
        client_gender = EXCLUDED.client_gender,
        client_address = EXCLUDED.client_address,
        client_citizenship = EXCLUDED.client_citizenship,
        client_telegram = EXCLUDED.client_telegram,
        deleted = FALSE,
        updated_at = now()
    RETURNING client_id
)
INSERT INTO _mobile_flow_ctx
SELECT
    COALESCE((SELECT client_id FROM existing_client), (SELECT client_id FROM inserted_client), 931059966),
    931059001,
    931059002,
    931059001,
    931059002,
    931059003,
    931059001,
    931059002,
    931059003,
    931059001,
    931059002,
    931059003;

INSERT INTO client_client_public_phone(public_phone, deleted, updated_at, created_at, client_id)
SELECT '+998931059966', FALSE, now(), now(), client_id
FROM _mobile_flow_ctx
WHERE NOT EXISTS (
    SELECT 1
    FROM client_client_public_phone
    WHERE public_phone = '+998931059966'
      AND COALESCE(deleted, FALSE) = FALSE
);

DO $$
DECLARE
    doctor_type_id INTEGER;
BEGIN
    SELECT user_type_id
    INTO doctor_type_id
    FROM user_user_type
    WHERE type_text IN ('Доктор', 'Doctor')
      AND COALESCE(deleted, FALSE) = FALSE
    ORDER BY CASE WHEN type_text = 'Доктор' THEN 0 ELSE 1 END, user_type_id
    LIMIT 1;

    IF doctor_type_id IS NULL THEN
        RAISE EXCEPTION 'Doctor user type was not found in user_user_type';
    END IF;

    INSERT INTO user_user(
        id, password, is_superuser, username, is_active, is_staff,
        user_firstname, user_lastname, user_father_name, user_birthdate,
        user_gender, user_address, user_citizenship, user_telegram,
        user_on_place, user_is_active, user_salary_percent, user_salary_child_percent,
        user_has_car, user_image, archive, deleted, updated_at, created_at,
        user_type_id, user_color, user_auth_code, user_code_max_try, user_code_period
    )
    VALUES
    (
        931059001, '!', FALSE, 'mock.dr.sarvar.931059966', TRUE, FALSE,
        'Sarvar', 'Turgunov', 'Akmalovich', '1987-02-15',
        'Male', 'Toshkent', 'UZ', '@dr_sarvar_mock',
        TRUE, TRUE, 30, 0, FALSE, NULL, FALSE, FALSE,
        now(), now(), doctor_type_id, '#38BFA7', NULL, '0', NULL
    ),
    (
        931059002, '!', FALSE, 'mock.dr.dinara.931059966', TRUE, FALSE,
        'Dinara', 'Abdurazakova', 'Rustamovna', '1991-08-21',
        'Female', 'Toshkent', 'UZ', '@dr_dinara_mock',
        TRUE, TRUE, 25, 0, FALSE, NULL, FALSE, FALSE,
        now(), now(), doctor_type_id, '#7ECF95', NULL, '0', NULL
    )
    ON CONFLICT (id) DO UPDATE SET
        user_firstname = EXCLUDED.user_firstname,
        user_lastname = EXCLUDED.user_lastname,
        user_gender = EXCLUDED.user_gender,
        user_type_id = EXCLUDED.user_type_id,
        user_color = EXCLUDED.user_color,
        deleted = FALSE,
        updated_at = now();
END
$$;

INSERT INTO work_work(
    work_id, work_type, work_salary_type, work_title,
    work_title_ru, work_title_en, work_title_uz,
    work_basic_price, work_vip_price, work_null_price,
    work_discount_percent, work_discount_price,
    work_fixed_salary_amount, work_hybrid_salary_amount,
    archive, deleted, updated_at, created_at, estimated_duration_days
)
VALUES
(
    931059001, 'Common', 'Percent', 'Gigiyenik tishlarni tozalash',
    'Гигиеническая чистка зубов', 'Professional dental cleaning', 'Gigiyenik tishlarni tozalash',
    200000, 250000, 0, 0, 200000, 0, 0,
    FALSE, FALSE, now(), now(), 7
),
(
    931059002, 'Common', 'Percent', 'Zoom-4 texnologiyasi orqali oqartirish',
    'Отбеливание зубов Zoom-4', 'Zoom-4 teeth whitening', 'Zoom-4 texnologiyasi orqali oqartirish',
    900000, 1000000, 0, 0, 900000, 0, 0,
    FALSE, FALSE, now(), now(), 14
),
(
    931059003, 'Common', 'Percent', 'Plomba va karies davolash',
    'Лечение кариеса и пломба', 'Filling and caries treatment', 'Plomba va karies davolash',
    350000, 400000, 0, 0, 350000, 0, 0,
    FALSE, FALSE, now(), now(), 3
)
ON CONFLICT (work_id) DO UPDATE SET
    work_title = EXCLUDED.work_title,
    work_title_ru = EXCLUDED.work_title_ru,
    work_title_en = EXCLUDED.work_title_en,
    work_title_uz = EXCLUDED.work_title_uz,
    work_basic_price = EXCLUDED.work_basic_price,
    work_vip_price = EXCLUDED.work_vip_price,
    work_discount_price = EXCLUDED.work_discount_price,
    estimated_duration_days = EXCLUDED.estimated_duration_days,
    deleted = FALSE,
    updated_at = now();

DELETE FROM transaction_transaction
WHERE transaction_id IN (
    '93105966-0001-4001-8001-000000000001',
    '93105966-0002-4002-8002-000000000002',
    '93105966-0003-4003-8003-000000000003'
);
DELETE FROM medcard_action WHERE action_id IN (931059001, 931059002, 931059003, 931059004, 931059005);
DELETE FROM medcard_stage WHERE stage_id IN (931059001, 931059002, 931059003);
DELETE FROM medcard_medicalcard WHERE card_id IN (931059001, 931059002, 931059003);
DELETE FROM reservation_reservationrequest WHERE id IN (931059001, 931059002);
DELETE FROM reservation_reservation WHERE reservation_id IN (931059001, 931059002, 931059003);
DELETE FROM medcard_tooth WHERE tooth_id IN (931059001, 931059002, 931059003);

INSERT INTO medcard_tooth(
    tooth_id, tooth_type, tooth_number, tooth_image,
    updated_at, created_at, archive, deleted
)
VALUES
    (931059001, 'Adult', '11', 'teeth/11.png', now(), now(), FALSE, FALSE),
    (931059002, 'Adult', '21', 'teeth/21.png', now(), now(), FALSE, FALSE),
    (931059003, 'Adult', '36', 'teeth/36.png', now(), now(), FALSE, FALSE)
ON CONFLICT (tooth_id) DO UPDATE SET
    tooth_number = EXCLUDED.tooth_number,
    deleted = FALSE,
    updated_at = now();

INSERT INTO reservation_reservation(
    reservation_id, reservation_notes, reservation_date, reservation_start_time,
    cancelled, created_at, reservation_client_id, reservation_doctor_id,
    reservation_end_time, reservation_work_id, cancelled_by_patient, is_initial
)
SELECT reservation_one_id, 'Mobile mock: clinic accepted upcoming appointment',
       current_date + 1, '09:00'::time, FALSE, now() - interval '1 day',
       client_id, doctor_one_id, '10:00'::time, work_one_id, FALSE, TRUE
FROM _mobile_flow_ctx
UNION ALL
SELECT reservation_two_id, 'Mobile mock: in-progress treatment visit',
       current_date - 2, '14:00'::time, FALSE, now() - interval '5 days',
       client_id, doctor_two_id, '15:00'::time, work_two_id, FALSE, FALSE
FROM _mobile_flow_ctx
UNION ALL
SELECT reservation_three_id, 'Mobile mock: completed treatment visit',
       current_date - 18, '11:00'::time, FALSE, now() - interval '20 days',
       client_id, doctor_one_id, '12:00'::time, work_three_id, FALSE, FALSE
FROM _mobile_flow_ctx;

DO $$
DECLARE
    ctx RECORD;
    existing_request_id INTEGER;
BEGIN
    SELECT * INTO ctx FROM _mobile_flow_ctx LIMIT 1;

    SELECT rr.id
    INTO existing_request_id
    FROM reservation_reservationrequest rr
    WHERE rr.client_id = ctx.client_id
      AND rr.status IN ('draft', 'approved')
      AND rr.reservation_id IS NULL
    ORDER BY rr.created_at DESC
    LIMIT 1;

    IF existing_request_id IS NOT NULL THEN
        UPDATE reservation_reservationrequest
        SET status = 'approved',
            reservation_id = ctx.reservation_one_id,
            doctor_id = ctx.doctor_one_id,
            reservation_work_id = ctx.work_one_id,
            doctor_name = 'Sarvar Turgunov',
            date = current_date + 1,
            time = '09:00'::time,
            note = 'Accepted existing mobile reservation request for 998931059966',
            updated_at = now()
        WHERE id = existing_request_id;
    ELSE
        INSERT INTO reservation_reservationrequest(
            id, created_at, updated_at, flutter_reservation_id, status,
            doctor_name, note, date, time,
            client_id, doctor_id, reservation_id, reservation_work_id
        )
        VALUES (
            931059001, now() - interval '2 hours', now(),
            'mock-998931059966-accepted', 'approved',
            'Sarvar Turgunov',
            'Inserted accepted mobile reservation request for 998931059966',
            current_date + 1, '09:00'::time,
            ctx.client_id, ctx.doctor_one_id, ctx.reservation_one_id, ctx.work_one_id
        );
    END IF;

    INSERT INTO reservation_reservationrequest(
        id, created_at, updated_at, flutter_reservation_id, status,
        doctor_name, note, date, time,
        client_id, doctor_id, reservation_id, reservation_work_id
    )
    VALUES (
        931059002, now() - interval '20 minutes', now() - interval '20 minutes',
        'mock-998931059966-draft', 'draft',
        'Dinara Abdurazakova',
        'Pending mobile request for UI status check',
        current_date + 6, '16:00'::time,
        ctx.client_id, ctx.doctor_two_id, NULL, ctx.work_two_id
    )
    ON CONFLICT (id) DO UPDATE SET
        status = 'draft',
        reservation_id = NULL,
        updated_at = now(),
        date = EXCLUDED.date,
        time = EXCLUDED.time;
END
$$;

INSERT INTO medcard_medicalcard(
    card_id, card_price, card_discount_price, card_discount_percent,
    card_is_done, card_is_paid, card_is_cancelled, card_finished_at,
    card_updated_at, card_created_at, archive, deleted, client_id
)
SELECT card_one_id, 650000, 650000, 0, FALSE, FALSE, FALSE, NULL::timestamp with time zone,
       now(), now() - interval '7 days', FALSE, FALSE, client_id
FROM _mobile_flow_ctx
UNION ALL
SELECT card_two_id, 900000, 900000, 0, FALSE, FALSE, FALSE, NULL::timestamp with time zone,
       now(), now() - interval '12 days', FALSE, FALSE, client_id
FROM _mobile_flow_ctx
UNION ALL
SELECT card_three_id, 350000, 350000, 0, TRUE, TRUE, FALSE, now() - interval '18 days',
       now() - interval '18 days', now() - interval '25 days', FALSE, FALSE, client_id
FROM _mobile_flow_ctx;

INSERT INTO medcard_stage(
    stage_id, stage_is_done, stage_is_paid, stage_is_cancelled, stage_index,
    updated_at, created_at, archive, deleted, card_id, stage_created_by_id, tooth_id
)
VALUES
    (931059001, FALSE, FALSE, FALSE, 1, now(), now() - interval '7 days', FALSE, FALSE, 931059001, 931059001, 931059001),
    (931059002, FALSE, FALSE, FALSE, 1, now(), now() - interval '12 days', FALSE, FALSE, 931059002, 931059002, 931059002),
    (931059003, TRUE, TRUE, FALSE, 1, now() - interval '18 days', now() - interval '25 days', FALSE, FALSE, 931059003, 931059001, 931059003);

INSERT INTO medcard_action(
    action_id, action_note, action_quantity, action_price, action_price_type,
    action_is_done, action_is_paid, action_is_cancelled, action_finished_at,
    updated_at, created_at, archive, deleted,
    action_created_by_id, action_date_id, action_disease_id,
    action_doctor_id, action_stage_id, action_work_id
)
VALUES
(
    931059001, 'Qabul tabida korinadigan upcoming gigiyena qabuli',
    1, 200000, 'Basic', FALSE, FALSE, FALSE, NULL,
    now(), now() - interval '7 days', FALSE, FALSE,
    931059001, 931059001, NULL, 931059001, 931059001, 931059001
),
(
    931059002, 'Davolanish rejasi: Zoom-4 oqartirish',
    1, 900000, 'Basic', TRUE, FALSE, FALSE, now() - interval '2 days',
    now(), now() - interval '12 days', FALSE, FALSE,
    931059002, 931059002, NULL, 931059002, 931059002, 931059002
),
(
    931059003, 'Davolanish rejasi: qoshimcha gigiyena nazorati',
    1, 200000, 'Basic', FALSE, FALSE, FALSE, NULL,
    now(), now() - interval '11 days', FALSE, FALSE,
    931059002, NULL, NULL, 931059002, 931059002, 931059001
),
(
    931059004, 'Otilgan davolanish: plomba va karies davolash',
    1, 350000, 'Basic', TRUE, TRUE, FALSE, now() - interval '18 days',
    now() - interval '18 days', now() - interval '25 days', FALSE, FALSE,
    931059001, 931059003, NULL, 931059001, 931059003, 931059003
);

INSERT INTO transaction_transaction(
    transaction_id, transaction_type, transaction_payment_type,
    transaction_sum, transaction_action_price, transaction_discount_price,
    transaction_discount_percent, transaction_work_basic_price,
    transaction_work_vip_price, transaction_work_discount_price,
    transaction_work_discount_percent, transaction_card_discount_price,
    transaction_card_discount_percent, transaction_benefit, transaction_loss,
    transaction_created_at, transaction_updated_at,
    transaction_action_id, transaction_card_id, transaction_client_id,
    transaction_credit_id, transaction_receiver_id, transaction_user_id,
    financial_report_id, updated_by_id, comment
)
SELECT '93105966-0001-4001-8001-000000000001'::uuid,
       'pay_for_action', 'cash', 100000, 200000, 0,
       0, 200000, 250000, 200000, 0, 650000,
       0, 0, 0, now() - interval '1 day', now() - interval '1 day',
       931059001, 931059001, client_id, NULL::integer, NULL::integer, doctor_one_id,
       NULL::integer, NULL::bigint, 'Mock prepayment for upcoming accepted visit'
FROM _mobile_flow_ctx
UNION ALL
SELECT '93105966-0002-4002-8002-000000000002'::uuid,
       'pay_for_action', 'terminal', 250000, 900000, 0,
       0, 900000, 1000000, 900000, 0, 900000,
       0, 0, 0, now() - interval '4 days', now() - interval '4 days',
       931059002, 931059002, client_id, NULL::integer, NULL::integer, doctor_two_id,
       NULL::integer, NULL::bigint, 'Mock partial payment for in-progress treatment'
FROM _mobile_flow_ctx
UNION ALL
SELECT '93105966-0003-4003-8003-000000000003'::uuid,
       'pay_for_action', 'cash', 350000, 350000, 0,
       0, 350000, 400000, 350000, 0, 350000,
       0, 0, 0, now() - interval '18 days', now() - interval '18 days',
       931059004, 931059003, client_id, NULL::integer, NULL::integer, doctor_one_id,
       NULL::integer, NULL::bigint, 'Mock full payment for completed treatment'
FROM _mobile_flow_ctx;

SELECT 'seeded_crm_client_id' AS key, client_id AS value FROM _mobile_flow_ctx;

COMMIT;
