-- =============================================================================
-- Staging seed data for Medi-Nudge demo
-- Run against: medinudge database on RDS staging
-- Login after seeding: coordinator@medi-nudge.demo / Demo1234!
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Care coordinator user
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO users (email, hashed_password, full_name, is_active, created_at)
VALUES (
  'coordinator@medi-nudge.demo',
  '$2b$12$x0STGNS7s45PL1GekOne7udBurMWUZU0cSCmeNYD2',
  'Demo Coordinator',
  true,
  NOW()
)
ON CONFLICT (email) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Patients
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO patients (full_name, phone_number, nric_hash, language_preference, risk_level,
  conditions, onboarding_state, is_active, caregiver_name, caregiver_phone_number,
  consent_obtained_at, created_at, updated_at)
VALUES
  ('Tan Wei Liang',        '+6591234001', '346f6b33df5b3b983835b1e9b3f88973f5b1933be774019ffb81b46a1c8885aa',
   'en', 'high',   '["Hypertension","Diabetes Mellitus Type 2"]'::json,
   'complete', true, 'Tan Mei Ling', '+6598765001', NOW()-INTERVAL '30 days', NOW(), NOW()),
  ('Lim Ah Kow',           '+6591234002', '11b435b250a129d2b2f42ff018ca82d753432e7e4292f8ac2debb847776fc609',
   'en', 'normal', '["Hypertension","Hyperlipidaemia"]'::json,
   'complete', true, NULL, NULL,                   NOW()-INTERVAL '45 days', NOW(), NOW()),
  ('Siti Rahimah',         '+6591234003', 'd3b63f3f35e376cf04cc5e8a5054569dbc249101282b703cff102dc6075900c9',
   'ms', 'low',    '["Diabetes Mellitus Type 2"]'::json,
   'complete', true, 'Ahmad Rahimi', '+6598765003', NOW()-INTERVAL '20 days', NOW(), NOW()),
  ('Rajan Krishnamurthy',  '+6591234004', 'a1c52be958288fca893ee4d7bb2b0939db1f8f78039e8910095c40a6d978bef9',
   'en', 'high',   '["Coronary Artery Disease","Hypertension","Hyperlipidaemia"]'::json,
   'complete', true, 'Priya Rajan', '+6598765004',  NOW()-INTERVAL '60 days', NOW(), NOW()),
  ('Chen Mei Fong',        '+6591234005', '033700e3e7fcfdcccac2c6a0869006010604711a1377d759e40b000bed4bfb50',
   'zh', 'normal', '["Hypothyroidism","Hypertension"]'::json,
   'complete', true, NULL, NULL,                   NOW()-INTERVAL '15 days', NOW(), NOW()),
  ('Ahmad Zulkifli',       '+6591234006', 'f0701222807732b8ce64ea87452fed10d69a13df6aec7c13565f23d4ccb9eeff',
   'ms', 'high',   '["Heart Failure","Hypertension"]'::json,
   'complete', true, 'Fatimah Zulkifli', '+6598765006', NOW()-INTERVAL '50 days', NOW(), NOW()),
  ('Wong Beng Huat',       '+6591234007', '0f4acb1be740f2e0f591546c62c918a933c257ce02a5a1ed23ef3863d30c5cf3',
   'zh', 'low',    '["Hyperlipidaemia","GERD"]'::json,
   'complete', true, NULL, NULL,                   NOW()-INTERVAL '10 days', NOW(), NOW()),
  ('Kavitha Subramaniam',  '+6591234008', 'e18924d966134782970abdd9c580f84feafe911ef5e8c6b19ad60d043977c202',
   'en', 'normal', '["Asthma","Anxiety Disorder"]'::json,
   'complete', true, NULL, NULL,                   NOW()-INTERVAL '25 days', NOW(), NOW()),
  ('Lee Chong Meng',       '+6591234009', '6d1699def25472e1f2f08420efaf4a12174ed3faa2609fd324b623b079ee6bc5',
   'zh', 'high',   '["Diabetes Mellitus Type 2","Chronic Kidney Disease"]'::json,
   'complete', true, 'Lee Sok Hua', '+6598765009',  NOW()-INTERVAL '40 days', NOW(), NOW()),
  ('Nurul Huda Binte Ismail', '+6591234010', '95d2d444b046597f2643365eaa5feca42dd09bcd33ba3adb8b41d2592c2bec55',
   'ms', 'low',    '["Hypertension"]'::json,
   'complete', true, NULL, NULL,                   NOW()-INTERVAL '5 days',  NOW(), NOW())
ON CONFLICT (phone_number) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Patient medications
--    Assigns 2-4 meds per patient based on their conditions.
--    Uses subqueries to look up patient_id and medication_id by name.
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO patient_medications
  (patient_id, medication_id, dosage, frequency, reminder_times,
   refill_interval_days, is_active, created_at)
SELECT p.id, m.id, dosage, freq, to_json(times::text[]), 30,
       true, NOW()
FROM (VALUES
  -- Tan Wei Liang — Hypertension + Diabetes
  ('+6591234001', 'Amlodipine',    '10mg',  'once_daily',  '{"08:00"}'),
  ('+6591234001', 'Metformin',     '500mg', 'twice_daily', '{"08:00","20:00"}'),
  ('+6591234001', 'Empagliflozin', '10mg',  'once_daily',  '{"08:00"}'),
  -- Lim Ah Kow — Hypertension + Hyperlipidaemia
  ('+6591234002', 'Losartan',      '50mg',  'once_daily',  '{"08:00"}'),
  ('+6591234002', 'Atorvastatin',  '20mg',  'once_daily',  '{"21:00"}'),
  -- Siti Rahimah — Diabetes
  ('+6591234003', 'Metformin',     '850mg', 'twice_daily', '{"08:00","20:00"}'),
  ('+6591234003', 'Gliclazide',    '30mg',  'once_daily',  '{"08:00"}'),
  -- Rajan Krishnamurthy — CAD + Hypertension + Hyperlipidaemia
  ('+6591234004', 'Acetylsalicylic Acid', '100mg', 'once_daily', '{"08:00"}'),
  ('+6591234004', 'Bisoprolol',    '5mg',   'once_daily',  '{"08:00"}'),
  ('+6591234004', 'Atorvastatin',  '40mg',  'once_daily',  '{"21:00"}'),
  ('+6591234004', 'Amlodipine',    '5mg',   'once_daily',  '{"08:00"}'),
  -- Chen Mei Fong — Hypothyroidism + Hypertension
  ('+6591234005', 'Levothyroxine', '50mg',  'once_daily',  '{"07:00"}'),
  ('+6591234005', 'Losartan',      '25mg',  'once_daily',  '{"08:00"}'),
  -- Ahmad Zulkifli — Heart Failure + Hypertension
  ('+6591234006', 'Bisoprolol',    '10mg',  'once_daily',  '{"08:00"}'),
  ('+6591234006', 'Lisinopril',    '5mg',   'once_daily',  '{"08:00"}'),
  ('+6591234006', 'Empagliflozin', '10mg',  'once_daily',  '{"08:00"}'),
  -- Wong Beng Huat — Hyperlipidaemia + GERD
  ('+6591234007', 'Rosuvastatin',  '10mg',  'once_daily',  '{"21:00"}'),
  ('+6591234007', 'Omeprazole',    '20mg',  'once_daily',  '{"08:00"}'),
  -- Kavitha Subramaniam — Asthma + Anxiety
  ('+6591234008', 'Salbutamol',    '100mcg','once_daily',  '{"08:00"}'),
  ('+6591234008', 'Escitalopram',  '10mg',  'once_daily',  '{"08:00"}'),
  -- Lee Chong Meng — Diabetes + CKD
  ('+6591234009', 'Metformin',     '500mg', 'twice_daily', '{"08:00","20:00"}'),
  ('+6591234009', 'Losartan',      '50mg',  'once_daily',  '{"08:00"}'),
  -- Nurul Huda — Hypertension
  ('+6591234010', 'Amlodipine',    '5mg',   'once_daily',  '{"08:00"}')
) AS v(phone, med_name, dosage, freq, times)
JOIN patients p ON p.phone_number = v.phone
JOIN medications m ON m.generic_name = v.med_name
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Dose logs — 30 days of history per patient medication
--    taken/missed based on risk_level adherence rate
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO dose_logs (patient_id, medication_id, patient_medication_id, status, source, logged_at, created_at)
SELECT
  pm.patient_id,
  pm.medication_id,
  pm.id,
  CASE
    WHEN p.risk_level = 'high'   AND random() < 0.65 THEN 'taken'
    WHEN p.risk_level = 'normal' AND random() < 0.80 THEN 'taken'
    WHEN p.risk_level = 'low'    AND random() < 0.92 THEN 'taken'
    ELSE 'missed'
  END,
  'system_detected',
  (CURRENT_DATE - (gs_day.day * INTERVAL '1 day'))
    + (CASE WHEN pm.frequency = 'twice_daily' AND gs_dose.dose_num = 1 THEN INTERVAL '20 hours'
            ELSE INTERVAL '8 hours' END),
  NOW()
FROM patient_medications pm
JOIN patients p ON p.id = pm.patient_id
CROSS JOIN generate_series(1, 30) AS gs_day(day)
CROSS JOIN generate_series(0, CASE WHEN pm.frequency = 'twice_daily' THEN 1 ELSE 0 END) AS gs_dose(dose_num)
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Escalations for high-risk patients
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO escalation_cases (patient_id, reason, priority, status, created_at, updated_at)
SELECT p.id,
  'Consecutive missed doses — high risk patient requires follow-up',
  'urgent', 'open', NOW() - INTERVAL '2 days', NOW()
FROM patients p
WHERE p.risk_level = 'high'
  AND p.phone_number IN ('+6591234001','+6591234004','+6591234006','+6591234009')
ON CONFLICT DO NOTHING;

COMMIT;
