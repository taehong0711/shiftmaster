-- migrations/003_add_constraints.sql
-- 동적 제약 조건 테이블 추가

-- Constraints 테이블
CREATE TABLE IF NOT EXISTS constraints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'coverage',  -- 'coverage'|'sequence'|'balance'|'preference'|'skill'
    constraint_type TEXT NOT NULL DEFAULT 'soft',  -- 'hard'|'soft'
    is_enabled BOOLEAN DEFAULT TRUE,
    penalty_weight INTEGER DEFAULT 10000,
    priority_order INTEGER DEFAULT 50,
    rule_definition JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(branch_id, code)
);

CREATE INDEX IF NOT EXISTS idx_constraints_branch ON constraints(branch_id);
CREATE INDEX IF NOT EXISTS idx_constraints_code ON constraints(code);
CREATE INDEX IF NOT EXISTS idx_constraints_category ON constraints(category);
CREATE INDEX IF NOT EXISTS idx_constraints_type ON constraints(constraint_type);
CREATE INDEX IF NOT EXISTS idx_constraints_enabled ON constraints(is_enabled);
CREATE INDEX IF NOT EXISTS idx_constraints_priority ON constraints(priority_order);

-- RLS 활성화
ALTER TABLE constraints ENABLE ROW LEVEL SECURITY;

-- 트리거
CREATE TRIGGER update_constraints_updated_at BEFORE UPDATE ON constraints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 기본 제약 조건 시드 데이터
-- 기본 지점의 제약 조건 초기화
DO $$
DECLARE
    default_branch_id UUID;
BEGIN
    SELECT id INTO default_branch_id FROM branches WHERE code = 'MAIN' LIMIT 1;

    IF default_branch_id IS NOT NULL THEN
        -- 이미 제약이 있으면 건너뛰기
        IF NOT EXISTS (SELECT 1 FROM constraints WHERE branch_id = default_branch_id LIMIT 1) THEN

            -- 하드 제약
            INSERT INTO constraints (branch_id, name, code, category, constraint_type, is_enabled, penalty_weight, priority_order, rule_definition)
            VALUES
            (default_branch_id, 'night_after_night_off', 'NIGHT_AFTER_OFF', 'sequence', 'hard', TRUE, 200000, 1,
             '{"type": "sequence", "description_ja": "夜勤後は必ず明け休み", "description_ko": "야간 근무 후 반드시 휴무", "description_en": "Off day required after night shift", "rule": {"after_shifts": ["Q1", "X1", "R1"], "next_day_must_be": ["-"]}}'::jsonb),

            (default_branch_id, 'max_consecutive_work', 'MAX_CONSEC_WORK', 'sequence', 'hard', TRUE, 200000, 2,
             '{"type": "rolling_window", "description_ja": "連続勤務は最大5日", "description_ko": "연속 근무 최대 5일", "description_en": "Maximum 5 consecutive work days", "rule": {"max_consecutive_work_days": 5}}'::jsonb),

            (default_branch_id, 'one_shift_per_day', 'ONE_SHIFT_DAY', 'coverage', 'hard', TRUE, 200000, 3,
             '{"type": "basic", "description_ja": "1日1シフトのみ", "description_ko": "하루 1시프트만", "description_en": "One shift per day only", "rule": {"exactly_one_shift_per_day": true}}'::jsonb),

            (default_branch_id, 'skill_required', 'SKILL_REQ', 'skill', 'hard', TRUE, 200000, 4,
             '{"type": "skill_match", "description_ja": "スキル要件を満たす必要あり", "description_ko": "스킬 요건 충족 필수", "description_en": "Skill requirements must be met", "rule": {"shift_skill_map": {"L1": "L1", "Q1": "NIGHT", "X1": "NIGHT", "R1": "NIGHT"}}}'::jsonb),

            (default_branch_id, 'ng_shifts_forbidden', 'NG_FORBIDDEN', 'preference', 'hard', TRUE, 200000, 5,
             '{"type": "forbidden", "description_ja": "NG指定シフトは割り当て禁止", "description_ko": "NG 지정 시프트 배정 금지", "description_en": "NG designated shifts are forbidden", "rule": {"respect_ng_assignments": true}}'::jsonb),

            -- 소프트 제약
            (default_branch_id, 'request_satisfaction', 'REQ_SATISFY', 'preference', 'soft', TRUE, 50000, 10,
             '{"type": "preference", "description_ja": "希望シフトをなるべく満たす", "description_ko": "희망 시프트 최대한 충족", "description_en": "Satisfy shift requests as much as possible", "rule": {"maximize_request_satisfaction": true}}'::jsonb),

            (default_branch_id, 'target_off_days', 'TARGET_OFF', 'balance', 'soft', TRUE, 30000, 11,
             '{"type": "balance", "description_ja": "目標休日数に近づける", "description_ko": "목표 휴일 수 달성", "description_en": "Achieve target off days", "rule": {"target_off_days_field": "target_off", "deviation_penalty": true}}'::jsonb),

            (default_branch_id, 'night_shift_balance', 'NIGHT_BALANCE', 'balance', 'soft', TRUE, 20000, 12,
             '{"type": "balance", "description_ja": "夜勤を均等に配分", "description_ko": "야간 근무 균등 배분", "description_en": "Balance night shifts among staff", "rule": {"balance_shifts": ["Q1", "X1", "R1"], "among_staff_with_skill": "NIGHT"}}'::jsonb),

            (default_branch_id, 'min_daily_coverage', 'MIN_COVERAGE', 'coverage', 'soft', TRUE, 40000, 13,
             '{"type": "coverage", "description_ja": "日別最低人数を確保", "description_ko": "일별 최소 인원 확보", "description_en": "Ensure minimum daily coverage", "rule": {"min_staff_per_day": 3, "exclude_shifts": ["-", "公"]}}'::jsonb),

            (default_branch_id, 'weekend_balance', 'WEEKEND_BALANCE', 'balance', 'soft', TRUE, 15000, 14,
             '{"type": "balance", "description_ja": "週末勤務を均等に", "description_ko": "주말 근무 균등 배분", "description_en": "Balance weekend work", "rule": {"balance_weekend_work": true}}'::jsonb),

            (default_branch_id, 'l1_daily_coverage', 'L1_COVERAGE', 'coverage', 'soft', TRUE, 35000, 15,
             '{"type": "coverage", "description_ja": "毎日L1を1人配置", "description_ko": "매일 L1 1명 배치", "description_en": "One L1 shift per day", "rule": {"shift_code": "L1", "exactly_per_day": 1}}'::jsonb),

            (default_branch_id, 'avoid_split_weekends', 'AVOID_SPLIT_WEEKEND', 'preference', 'soft', TRUE, 10000, 16,
             '{"type": "preference", "description_ja": "土日の片方だけ勤務を避ける", "description_ko": "주말 분할 근무 회피", "description_en": "Avoid working only one weekend day", "rule": {"prefer_full_weekend_off_or_work": true}}'::jsonb),

            (default_branch_id, 'closed_day_night_count', 'CLOSED_NIGHT', 'coverage', 'soft', TRUE, 25000, 17,
             '{"type": "coverage", "description_ja": "休館日の夜勤人数", "description_ko": "휴관일 야간 인원", "description_en": "Night shift count on closed days", "rule": {"on_closed_days": true, "night_shift_count": 2}}'::jsonb);

        END IF;
    END IF;
END $$;
