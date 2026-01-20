-- migrations/001_initial.sql
-- 초기 스키마 (기존 테이블 유지)

-- Staff 테이블
CREATE TABLE IF NOT EXISTS staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID,
    name TEXT NOT NULL,
    gender TEXT DEFAULT 'M',
    role TEXT DEFAULT 'staff',
    target_off INTEGER DEFAULT 8,
    nenkyu INTEGER DEFAULT 0,
    skills TEXT DEFAULT '',
    prefer TEXT DEFAULT '',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staff_branch ON staff(branch_id);
CREATE INDEX IF NOT EXISTS idx_staff_name ON staff(name);
CREATE INDEX IF NOT EXISTS idx_staff_active ON staff(is_active);

-- Staff 감사 로그
CREATE TABLE IF NOT EXISTS staff_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID,
    action TEXT NOT NULL,
    before_data JSONB,
    after_data JSONB,
    performed_by TEXT,
    performed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications 테이블
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    type TEXT DEFAULT 'info',
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- Swap Requests 테이블
CREATE TABLE IF NOT EXISTS swap_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID,
    requester TEXT NOT NULL,
    target TEXT NOT NULL,
    swap_date DATE NOT NULL,
    requester_shift TEXT,
    target_shift TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_swap_status ON swap_requests(status);
CREATE INDEX IF NOT EXISTS idx_swap_requester ON swap_requests(requester);
CREATE INDEX IF NOT EXISTS idx_swap_target ON swap_requests(target);
CREATE INDEX IF NOT EXISTS idx_swap_date ON swap_requests(swap_date);

-- Monthly Shifts 테이블
CREATE TABLE IF NOT EXISTS monthly_shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    staff_name TEXT NOT NULL,
    shift_data JSONB NOT NULL DEFAULT '{}',
    off_days INTEGER DEFAULT 0,
    work_days INTEGER DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(branch_id, year, month, staff_name)
);

CREATE INDEX IF NOT EXISTS idx_monthly_shifts_ym ON monthly_shifts(year, month);
CREATE INDEX IF NOT EXISTS idx_monthly_shifts_staff ON monthly_shifts(staff_name);

-- Monthly Shifts Summary 테이블
CREATE TABLE IF NOT EXISTS monthly_shifts_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id UUID,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    summary_data JSONB NOT NULL DEFAULT '{}',
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(branch_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_summary_ym ON monthly_shifts_summary(year, month);

-- RLS 활성화
ALTER TABLE staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE swap_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_shifts_summary ENABLE ROW LEVEL SECURITY;

-- updated_at 자동 업데이트 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 각 테이블에 트리거 적용
CREATE TRIGGER update_staff_updated_at BEFORE UPDATE ON staff
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_swap_requests_updated_at BEFORE UPDATE ON swap_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_monthly_shifts_updated_at BEFORE UPDATE ON monthly_shifts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_monthly_summary_updated_at BEFORE UPDATE ON monthly_shifts_summary
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
