-- migrations/002_add_branches.sql
-- 다중 지점 지원을 위한 테이블 추가

-- Branches 테이블 (지점)
CREATE TABLE IF NOT EXISTS branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    timezone TEXT DEFAULT 'Asia/Tokyo',
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_branches_code ON branches(code);
CREATE INDEX IF NOT EXISTS idx_branches_active ON branches(is_active);

-- User-Branch 관계 테이블
CREATE TABLE IF NOT EXISTS user_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer',  -- 'super'|'editor'|'viewer'
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, branch_id)
);

CREATE INDEX IF NOT EXISTS idx_user_branches_user ON user_branches(user_id);
CREATE INDEX IF NOT EXISTS idx_user_branches_branch ON user_branches(branch_id);
CREATE INDEX IF NOT EXISTS idx_user_branches_primary ON user_branches(is_primary);

-- 기존 테이블에 branch_id 추가 (없는 경우)
DO $$
BEGIN
    -- staff 테이블
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'staff' AND column_name = 'branch_id') THEN
        ALTER TABLE staff ADD COLUMN branch_id UUID REFERENCES branches(id);
    END IF;

    -- notifications 테이블
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'notifications' AND column_name = 'branch_id') THEN
        ALTER TABLE notifications ADD COLUMN branch_id UUID REFERENCES branches(id);
    END IF;

    -- swap_requests 테이블
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'swap_requests' AND column_name = 'branch_id') THEN
        ALTER TABLE swap_requests ADD COLUMN branch_id UUID REFERENCES branches(id);
    END IF;

    -- monthly_shifts 테이블
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'monthly_shifts' AND column_name = 'branch_id') THEN
        ALTER TABLE monthly_shifts ADD COLUMN branch_id UUID REFERENCES branches(id);
    END IF;

    -- monthly_shifts_summary 테이블
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'monthly_shifts_summary' AND column_name = 'branch_id') THEN
        ALTER TABLE monthly_shifts_summary ADD COLUMN branch_id UUID REFERENCES branches(id);
    END IF;
END $$;

-- 지점별 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_staff_branch_id ON staff(branch_id);
CREATE INDEX IF NOT EXISTS idx_notifications_branch_id ON notifications(branch_id);
CREATE INDEX IF NOT EXISTS idx_swap_requests_branch_id ON swap_requests(branch_id);
CREATE INDEX IF NOT EXISTS idx_monthly_shifts_branch_id ON monthly_shifts(branch_id);
CREATE INDEX IF NOT EXISTS idx_monthly_summary_branch_id ON monthly_shifts_summary(branch_id);

-- RLS 활성화
ALTER TABLE branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_branches ENABLE ROW LEVEL SECURITY;

-- Branches 테이블 트리거
CREATE TRIGGER update_branches_updated_at BEFORE UPDATE ON branches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_branches_updated_at BEFORE UPDATE ON user_branches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 기본 지점 삽입 (없는 경우)
INSERT INTO branches (name, code, timezone, is_active, settings)
SELECT '本店', 'MAIN', 'Asia/Tokyo', TRUE, '{"is_default": true}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM branches WHERE code = 'MAIN');

-- 기존 데이터에 기본 지점 할당
DO $$
DECLARE
    default_branch_id UUID;
BEGIN
    SELECT id INTO default_branch_id FROM branches WHERE code = 'MAIN' LIMIT 1;

    IF default_branch_id IS NOT NULL THEN
        UPDATE staff SET branch_id = default_branch_id WHERE branch_id IS NULL;
        UPDATE notifications SET branch_id = default_branch_id WHERE branch_id IS NULL;
        UPDATE swap_requests SET branch_id = default_branch_id WHERE branch_id IS NULL;
        UPDATE monthly_shifts SET branch_id = default_branch_id WHERE branch_id IS NULL;
        UPDATE monthly_shifts_summary SET branch_id = default_branch_id WHERE branch_id IS NULL;
    END IF;
END $$;
