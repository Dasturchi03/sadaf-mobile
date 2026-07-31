BEGIN;

DO $$
BEGIN
    IF current_database() <> 'sadaf_test_db' THEN
        RAISE EXCEPTION 'Refusing to seed mock CRM data into database "%". Expected "sadaf_test_db".', current_database();
    END IF;
END
$$;

DELETE FROM transaction_transaction
WHERE transaction_id IN (
    '11111111-1111-4111-8111-111111111111',
    '22222222-2222-4222-8222-222222222222'
);
DELETE FROM medcard_action WHERE action_id IN (990001, 990002, 990003);
DELETE FROM medcard_stage WHERE stage_id IN (990001, 990002);
DELETE FROM medcard_medicalcard WHERE card_id IN (990001, 990002);
DELETE FROM reservation_reservation WHERE reservation_id IN (990001, 990002);
DELETE FROM medcard_tooth WHERE tooth_id IN (990001, 990002);
DELETE FROM client_client_public_phone WHERE client_phone_id IN (990001, 990002, 990003);
DELETE FROM client_client WHERE client_id IN (990001, 990002);
DELETE FROM user_user WHERE id IN (990001, 990002);
DELETE FROM work_work WHERE work_id IN (990001, 990002, 990003);
DELETE FROM about_articleimage WHERE photo_id IN (990001, 990002, 990003);
DELETE FROM about_article WHERE article_id IN (990001, 990002, 990003);
DELETE FROM vacancies_vacancy WHERE vacancy_id IN (990001, 990002);
DELETE FROM about_termsandconditions WHERE text_id IN (990001, 990002, 990003, 990004);
DELETE FROM about_contractdocument WHERE contract_id = 990001;
DELETE FROM about_contacts WHERE data_id = 990001;

INSERT INTO about_contacts(
    created_at, updated_at, data_id, address, location_latt, location_long,
    phone, telegram, facebook, instagram, youtube
)
VALUES (
    now(), now(), 990001,
    'Toshkent shahri, Yunusobod tumani, Amir Temur shoh kochasi 107B',
    '41.337170', '69.284560',
    '+998712005555', '@sadaf_dental', 'sadafdental', 'sadaf_dental', 'SadafDental'
);

INSERT INTO about_article(
    created_at, updated_at, article_id, article_type,
    article_title, article_title_uz, article_title_ru, article_title_en,
    article_body, article_body_uz, article_body_ru, article_body_en
)
VALUES
(
    now() - interval '2 days', now() - interval '2 days', 990001, 'news',
    'Sadaf Dental mobil ilovasi ishga tushdi',
    'Sadaf Dental mobil ilovasi ishga tushdi',
    'Запущено мобильное приложение Sadaf Dental',
    'Sadaf Dental mobile app is live',
    'Qabulga yozilish, davolanish tarixini korish va bildirishnomalarni olish endi mobil ilova orqali yanada qulay.',
    'Qabulga yozilish, davolanish tarixini korish va bildirishnomalarni olish endi mobil ilova orqali yanada qulay.',
    'Запись на прием, история лечения и уведомления теперь доступны в мобильном приложении.',
    'Booking appointments, treatment history, and notifications are now available in the mobile app.'
),
(
    now() - interval '5 days', now() - interval '5 days', 990002, 'advice',
    'Implantatsiyadan keyin parvarish',
    'Implantatsiyadan keyin parvarish',
    'Уход после имплантации',
    'Care after dental implantation',
    'Birinchi 24 soatda issiq ichimliklardan saqlaning, shifokor tavsiyalariga amal qiling va nazorat qabulini otkazib yubormang.',
    'Birinchi 24 soatda issiq ichimliklardan saqlaning, shifokor tavsiyalariga amal qiling va nazorat qabulini otkazib yubormang.',
    'В первые 24 часа избегайте горячих напитков, соблюдайте рекомендации врача и не пропускайте контрольный прием.',
    'Avoid hot drinks for the first 24 hours, follow your doctor instructions, and do not miss follow-up visits.'
),
(
    now() - interval '8 days', now() - interval '8 days', 990003, 'promotion',
    'Bolalar stomatologiyasi uchun tekshiruv haftaligi',
    'Bolalar stomatologiyasi uchun tekshiruv haftaligi',
    'Неделя детского стоматологического осмотра',
    'Children dental checkup week',
    '7 yoshdan 14 yoshgacha bolalar uchun profilaktik korik va gigiyena boyicha tavsiyalar.',
    '7 yoshdan 14 yoshgacha bolalar uchun profilaktik korik va gigiyena boyicha tavsiyalar.',
    'Профилактический осмотр и рекомендации по гигиене для детей от 7 до 14 лет.',
    'Preventive checkups and hygiene advice for children aged 7 to 14.'
);

INSERT INTO about_articleimage(created_at, updated_at, photo_id, article_image, article_id)
VALUES
    (now(), now(), 990001, 'articles/mock-mobile-app.jpg', 990001),
    (now(), now(), 990002, 'articles/mock-implant-care.jpg', 990002),
    (now(), now(), 990003, 'articles/mock-children-checkup.jpg', 990003);

INSERT INTO vacancies_vacancy(
    vacancy_id, title, title_uz, title_ru, title_en,
    description, description_uz, description_ru, description_en,
    requirements, requirements_uz, requirements_ru, requirements_en,
    responsibilities, responsibilities_uz, responsibilities_ru, responsibilities_en,
    conditions, conditions_uz, conditions_ru, conditions_en,
    salary_from, salary_to, address, phone, email, deadline,
    is_active, sort_order, updated_at, created_at
)
VALUES
(
    990001,
    'Stomatolog assistenti',
    'Stomatolog assistenti',
    'Ассистент стоматолога',
    'Dental assistant',
    'Sadaf Dental jamoasiga tajribali yoki organishga tayyor assistent qidirilmoqda.',
    'Sadaf Dental jamoasiga tajribali yoki organishga tayyor assistent qidirilmoqda.',
    'В команду Sadaf Dental требуется ассистент стоматолога.',
    'Sadaf Dental is looking for a dental assistant.',
    'Tibbiy kollej yoki universitet, sterilizatsiya qoidalarini bilish, xushmuomalalik.',
    'Tibbiy kollej yoki universitet, sterilizatsiya qoidalarini bilish, xushmuomalalik.',
    'Медицинское образование, знание стерилизации, аккуратность и вежливость.',
    'Medical education, sterilization knowledge, accuracy, and friendly communication.',
    'Shifokorga qabul davomida yordam berish, kabinetni tayyorlash, materiallarni nazorat qilish.',
    'Shifokorga qabul davomida yordam berish, kabinetni tayyorlash, materiallarni nazorat qilish.',
    'Помощь врачу на приеме, подготовка кабинета, контроль материалов.',
    'Assist doctors during appointments, prepare the room, and track materials.',
    'Rasmiy ish, smenali grafik, trening va osish imkoniyati.',
    'Rasmiy ish, smenali grafik, trening va osish imkoniyati.',
    'Официальная работа, сменный график, обучение и рост.',
    'Official employment, shifts, training, and growth.',
    3500000, 6000000, 'Toshkent, Yunusobod', '+998712005555',
    'hr@sadaf.local', current_date + 30, TRUE, 1, now(), now()
),
(
    990002,
    'Administrator',
    'Administrator',
    'Администратор',
    'Administrator',
    'Mijozlarni kutib olish va qabul jadvalini yuritish uchun administrator kerak.',
    'Mijozlarni kutib olish va qabul jadvalini yuritish uchun administrator kerak.',
    'Требуется администратор для приема пациентов и ведения расписания.',
    'We need an administrator to welcome patients and manage appointments.',
    'CRM bilan ishlash tajribasi, telefon etiketi, rus va ozbek tillari.',
    'CRM bilan ishlash tajribasi, telefon etiketi, rus va ozbek tillari.',
    'Опыт работы с CRM, телефонный этикет, русский и узбекский языки.',
    'CRM experience, phone etiquette, Uzbek and Russian languages.',
    'Qongiroqlarga javob berish, qabulni tasdiqlash, mijozlarga servis korsatish.',
    'Qongiroqlarga javob berish, qabulni tasdiqlash, mijozlarga servis korsatish.',
    'Ответы на звонки, подтверждение записей, клиентский сервис.',
    'Answer calls, confirm appointments, and support patients.',
    'Qulay ofis, KPI bonus, doimiy treninglar.',
    'Qulay ofis, KPI bonus, doimiy treninglar.',
    'Комфортный офис, KPI бонусы, регулярное обучение.',
    'Comfortable office, KPI bonus, regular training.',
    4000000, 7000000, 'Toshkent, Yunusobod', '+998712005555',
    'hr@sadaf.local', current_date + 45, TRUE, 2, now(), now()
);

INSERT INTO about_termsandconditions(
    created_at, updated_at, text_id, title, text_type,
    text, text_uz, text_ru, text_en, is_active
)
VALUES
(
    now(), now(), 990001, 'Foydalanish shartlari', 'terms_and_conditions',
    'Sadaf Dental mobil ilovasidan foydalanish shartlari. Qabul va bildirishnoma malumotlari test uchun tayyorlandi.',
    'Sadaf Dental mobil ilovasidan foydalanish shartlari. Qabul va bildirishnoma malumotlari test uchun tayyorlandi.',
    'Условия использования мобильного приложения Sadaf Dental. Данные записей и уведомлений подготовлены для теста.',
    'Terms of use for the Sadaf Dental mobile application. Appointment and notification data is prepared for testing.',
    TRUE
),
(
    now(), now(), 990002, 'Maxfiylik siyosati', 'privacy_policy',
    'Mobil ilova telefon raqami va profil malumotlarini xizmat korsatish uchun saqlaydi.',
    'Mobil ilova telefon raqami va profil malumotlarini xizmat korsatish uchun saqlaydi.',
    'Мобильное приложение хранит номер телефона и профильные данные для оказания сервиса.',
    'The mobile app stores phone and profile data to provide service.',
    TRUE
),
(
    now(), now(), 990003, 'Ilova haqida', 'about_app',
    'Sadaf Dental ilovasi qabulga yozilish, davolanish tarixi va cashback funksiyalari uchun yaratilgan.',
    'Sadaf Dental ilovasi qabulga yozilish, davolanish tarixi va cashback funksiyalari uchun yaratilgan.',
    'Приложение Sadaf Dental создано для записи, истории лечения и cashback функций.',
    'The Sadaf Dental app is built for appointments, treatment history, and cashback features.',
    TRUE
),
(
    now(), now(), 990004, 'Qabul eslatmalari', 'reservation_notes',
    'Qabul vaqtiga 10 daqiqa oldin kelish tavsiya qilinadi.',
    'Qabul vaqtiga 10 daqiqa oldin kelish tavsiya qilinadi.',
    'Рекомендуем приходить за 10 минут до приема.',
    'We recommend arriving 10 minutes before the appointment.',
    TRUE
);

INSERT INTO about_contractdocument(created_at, updated_at, contract_id, file, is_active)
VALUES (now(), now(), 990001, 'docs/sadaf_mobile_contract.pdf', TRUE);

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
    990001, '!', FALSE, 'mock.dr.bekzod', TRUE, FALSE,
    'Bekzod', 'Rahimov', 'Anvarovich', '1986-03-12',
    'male', 'Toshkent', 'UZ', '@dr_bekzod_mock',
    TRUE, TRUE, 30, 0, FALSE, NULL, FALSE, FALSE,
    now(), now(), NULL, '#2F80ED', NULL, '0', NULL
),
(
    990002, '!', FALSE, 'mock.dr.dilnoza', TRUE, FALSE,
    'Dilnoza', 'Kadirova', 'Rustamovna', '1990-07-24',
    'female', 'Toshkent', 'UZ', '@dr_dilnoza_mock',
    TRUE, TRUE, 25, 0, FALSE, NULL, FALSE, FALSE,
    now(), now(), NULL, '#27AE60', NULL, '0', NULL
);

INSERT INTO client_client(
    client_id, client_firstname, client_lastname, client_father_name,
    client_birthdate, client_gender, client_address, client_citizenship,
    client_telegram, client_type, client_balance, archive, deleted,
    updated_at, created_at, client_user_id, client_last_viewed_at, note,
    cashback_balance, loyalty_tier, referral_code, referred_by_id, total_spent_amount
)
VALUES
(
    990001, 'Ulugbek', 'Shermetov', 'Javlonbek ogli',
    '2003-04-13', 'male', 'Toshkent, Yunusobod tumani', 'UZ',
    '@Dasturchi_03', 'Basic', 450000, FALSE, FALSE,
    now(), now() - interval '90 days', NULL, now(), 'Mock mobile test client',
    120000, 'silver', 'CRM-MOCK-ULUGBEK', NULL, 7800000
);

INSERT INTO client_client_public_phone(
    client_phone_id, public_phone, deleted, updated_at, created_at, client_id
)
VALUES
    (990001, '+998990011122', FALSE, now(), now(), 990001),
    (990002, '+998990011123', FALSE, now(), now(), 990001);

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
    990001, 'service', 'percent', 'Implantatsiya konsultatsiyasi',
    'Консультация по имплантации', 'Implant consultation', 'Implantatsiya konsultatsiyasi',
    150000, 150000, 0, 0, 150000, 0, 0,
    FALSE, FALSE, now(), now(), 7
),
(
    990002, 'service', 'percent', 'Professional gigiyena',
    'Профессиональная гигиена', 'Professional hygiene', 'Professional gigiyena',
    450000, 500000, 0, 10, 405000, 0, 0,
    FALSE, FALSE, now(), now(), 3
),
(
    990003, 'service', 'percent', 'Ortodontik breket nazorati',
    'Контроль брекет-системы', 'Braces follow-up', 'Ortodontik breket nazorati',
    250000, 300000, 0, 0, 250000, 0, 0,
    FALSE, FALSE, now(), now(), 14
);

INSERT INTO medcard_tooth(
    tooth_id, tooth_type, tooth_number, tooth_image,
    updated_at, created_at, archive, deleted
)
VALUES
    (990001, 'adult', '16', 'teeth/16.png', now(), now(), FALSE, FALSE),
    (990002, 'adult', '36', 'teeth/36.png', now(), now(), FALSE, FALSE);

INSERT INTO reservation_reservation(
    reservation_id, reservation_notes, reservation_date, reservation_start_time,
    cancelled, created_at, reservation_client_id, reservation_doctor_id,
    reservation_end_time, reservation_work_id, cancelled_by_patient, is_initial
)
VALUES
(
    990001, 'Mock upcoming implant consultation', current_date + 1, '10:30',
    FALSE, now() - interval '2 days', 990001, 990001,
    '11:30', 990001, FALSE, TRUE
),
(
    990002, 'Mock completed hygiene visit', current_date - 12, '15:00',
    FALSE, now() - interval '14 days', 990001, 990002,
    '15:45', 990002, FALSE, FALSE
);

INSERT INTO medcard_medicalcard(
    card_id, card_price, card_discount_price, card_discount_percent,
    card_is_done, card_is_paid, card_is_cancelled, card_finished_at,
    card_updated_at, card_created_at, archive, deleted, client_id
)
VALUES
(
    990001, 1800000, 1650000, 8,
    FALSE, FALSE, FALSE, NULL,
    now(), now() - interval '20 days', FALSE, FALSE, 990001
),
(
    990002, 450000, 405000, 10,
    TRUE, TRUE, FALSE, now() - interval '12 days',
    now() - interval '12 days', now() - interval '16 days', FALSE, FALSE, 990001
);

INSERT INTO medcard_stage(
    stage_id, stage_is_done, stage_is_paid, stage_is_cancelled, stage_index,
    updated_at, created_at, archive, deleted, card_id, stage_created_by_id, tooth_id
)
VALUES
    (990001, FALSE, FALSE, FALSE, 1, now(), now() - interval '20 days', FALSE, FALSE, 990001, 990001, 990001),
    (990002, TRUE, TRUE, FALSE, 1, now() - interval '12 days', now() - interval '16 days', FALSE, FALSE, 990002, 990002, 990002);

INSERT INTO medcard_action(
    action_id, action_note, action_quantity, action_price, action_price_type,
    action_is_done, action_is_paid, action_is_cancelled, action_finished_at,
    updated_at, created_at, archive, deleted,
    action_created_by_id, action_date_id, action_disease_id,
    action_doctor_id, action_stage_id, action_work_id
)
VALUES
(
    990001, 'Boshlangich konsultatsiya va rentgen natijalarini korib chiqish',
    1, 150000, 'basic', FALSE, FALSE, FALSE, NULL,
    now(), now() - interval '20 days', FALSE, FALSE,
    990001, 990001, NULL, 990001, 990001, 990001
),
(
    990002, 'Implantatsiya rejasini tayyorlash',
    1, 1500000, 'basic', FALSE, FALSE, FALSE, NULL,
    now(), now() - interval '19 days', FALSE, FALSE,
    990001, NULL, NULL, 990001, 990001, 990001
),
(
    990003, 'Professional gigiyena yakunlandi',
    1, 405000, 'discount', TRUE, TRUE, FALSE, now() - interval '12 days',
    now() - interval '12 days', now() - interval '16 days', FALSE, FALSE,
    990002, 990002, NULL, 990002, 990002, 990002
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
VALUES
(
    '11111111-1111-4111-8111-111111111111',
    'income', 'cash', 500000, 150000, 0,
    0, 150000, 150000, 150000, 0, 1650000,
    8, 0, 0, now() - interval '3 days', now() - interval '3 days',
    990001, 990001, 990001, NULL, 990001, 990001,
    NULL, NULL, 'Mock partial payment for implant plan'
),
(
    '22222222-2222-4222-8222-222222222222',
    'income', 'card', 405000, 405000, 45000,
    10, 450000, 500000, 405000, 10, 405000,
    10, 0, 0, now() - interval '12 days', now() - interval '12 days',
    990003, 990002, 990001, NULL, 990001, 990002,
    NULL, NULL, 'Mock paid hygiene visit'
);

SELECT setval(pg_get_serial_sequence('about_contacts', 'data_id'), COALESCE((SELECT max(data_id) FROM about_contacts), 1), TRUE);
SELECT setval(pg_get_serial_sequence('about_article', 'article_id'), COALESCE((SELECT max(article_id) FROM about_article), 1), TRUE);
SELECT setval(pg_get_serial_sequence('about_articleimage', 'photo_id'), COALESCE((SELECT max(photo_id) FROM about_articleimage), 1), TRUE);
SELECT setval(pg_get_serial_sequence('vacancies_vacancy', 'vacancy_id'), COALESCE((SELECT max(vacancy_id) FROM vacancies_vacancy), 1), TRUE);
SELECT setval(pg_get_serial_sequence('about_termsandconditions', 'text_id'), COALESCE((SELECT max(text_id) FROM about_termsandconditions), 1), TRUE);
SELECT setval(pg_get_serial_sequence('about_contractdocument', 'contract_id'), COALESCE((SELECT max(contract_id) FROM about_contractdocument), 1), TRUE);
SELECT setval(pg_get_serial_sequence('user_user', 'id'), COALESCE((SELECT max(id) FROM user_user), 1), TRUE);
SELECT setval(pg_get_serial_sequence('client_client', 'client_id'), COALESCE((SELECT max(client_id) FROM client_client), 1), TRUE);
SELECT setval(pg_get_serial_sequence('client_client_public_phone', 'client_phone_id'), COALESCE((SELECT max(client_phone_id) FROM client_client_public_phone), 1), TRUE);
SELECT setval(pg_get_serial_sequence('work_work', 'work_id'), COALESCE((SELECT max(work_id) FROM work_work), 1), TRUE);
SELECT setval(pg_get_serial_sequence('medcard_tooth', 'tooth_id'), COALESCE((SELECT max(tooth_id) FROM medcard_tooth), 1), TRUE);
SELECT setval(pg_get_serial_sequence('reservation_reservation', 'reservation_id'), COALESCE((SELECT max(reservation_id) FROM reservation_reservation), 1), TRUE);
SELECT setval(pg_get_serial_sequence('medcard_medicalcard', 'card_id'), COALESCE((SELECT max(card_id) FROM medcard_medicalcard), 1), TRUE);
SELECT setval(pg_get_serial_sequence('medcard_stage', 'stage_id'), COALESCE((SELECT max(stage_id) FROM medcard_stage), 1), TRUE);
SELECT setval(pg_get_serial_sequence('medcard_action', 'action_id'), COALESCE((SELECT max(action_id) FROM medcard_action), 1), TRUE);

COMMIT;
