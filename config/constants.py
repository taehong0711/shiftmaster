# config/constants.py
"""상수 정의 모듈"""

# 앱 정보
APP_NAME = "Hotel Shift Pro"
APP_VERSION = "2.0.0"

# 시프트 코드
DEFAULT_DAY_SHIFTS = ["E1", "E2", "G1", "G1U", "H1", "H2", "I1", "I2", "L1"]
DEFAULT_NIGHT_SHIFTS = ["Q1", "X1", "R1"]

# 특수 시프트 코드
SHIFT_OFF = "-"  # 휴무 (명け)
SHIFT_PUBLIC_OFF = "公"  # 공휴일
SHIFT_SUNDAY = "日"  # 일요일

# 스킬 코드
SKILL_L1 = "L1"
SKILL_NIGHT = "NIGHT"

# 역할 정의
ROLE_SUPER = "super"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"

ROLES = {
    ROLE_SUPER: {"name_ja": "管理者", "name_ko": "관리자", "name_en": "Super Admin"},
    ROLE_EDITOR: {"name_ja": "編集者", "name_ko": "편집자", "name_en": "Editor"},
    ROLE_VIEWER: {"name_ja": "閲覧者", "name_ko": "열람자", "name_en": "Viewer"},
}

# 제약 카테고리
CONSTRAINT_CATEGORIES = {
    "coverage": {"name_ja": "人員配置", "name_ko": "인원배치", "name_en": "Coverage"},
    "sequence": {"name_ja": "連続勤務", "name_ko": "연속근무", "name_en": "Sequence"},
    "balance": {"name_ja": "バランス", "name_ko": "균형", "name_en": "Balance"},
    "preference": {"name_ja": "希望", "name_ko": "희망", "name_en": "Preference"},
    "skill": {"name_ja": "スキル", "name_ko": "스킬", "name_en": "Skill"},
}

# 제약 유형
CONSTRAINT_TYPE_HARD = "hard"
CONSTRAINT_TYPE_SOFT = "soft"

# 페널티 가중치 기본값
DEFAULT_PENALTY_WEIGHTS = {
    "hard": 200000,
    "high": 50000,
    "medium": 10000,
    "low": 1000,
}

# 타임존
DEFAULT_TIMEZONE = "Asia/Tokyo"

# 지원 언어
SUPPORTED_LANGUAGES = {
    "ja": "日本語",
    "ko": "한국어",
    "en": "English",
}

DEFAULT_LANGUAGE = "ja"

# 페이지 정의
PAGES = {
    "dashboard": {"icon": "📊", "name_ja": "ダッシュボード", "name_ko": "대시보드", "name_en": "Dashboard"},
    "schedule": {"icon": "📅", "name_ja": "シフト生成", "name_ko": "시프트 생성", "name_en": "Schedule"},
    "requests": {"icon": "📝", "name_ja": "希望・NG入力", "name_ko": "희망/NG 입력", "name_en": "Requests"},
    "staff": {"icon": "👥", "name_ja": "スタッフ管理", "name_ko": "스태프 관리", "name_en": "Staff"},
    "constraints": {"icon": "⚙️", "name_ja": "制約条件", "name_ko": "제약조건", "name_en": "Constraints"},
    "branches": {"icon": "🏨", "name_ja": "支店管理", "name_ko": "지점 관리", "name_en": "Branches"},
    "swap": {"icon": "🔄", "name_ja": "シフト交換", "name_ko": "시프트 교환", "name_en": "Swap"},
    "settings": {"icon": "⚙️", "name_ja": "設定", "name_ko": "설정", "name_en": "Settings"},
}

# 시프트 색상 (Excel/HTML 표시용)
SHIFT_COLORS = {
    "night": "#FFCDD2",  # 빨간색 계열 (야간)
    "off": "#E0E0E0",    # 회색 (휴무)
    "public": "#C8E6C9", # 녹색 (공휴일)
    "l1": "#E1BEE7",     # 보라색 (L1)
    "early": "#BBDEFB",  # 파란색 (조기)
    "late": "#FFE0B2",   # 주황색 (늦은)
    "mid": "#FFF9C4",    # 노란색 (중간)
    "request": "#90CAF9", # 파란색 (희망 충족)
}

# 솔버 설정
SOLVER_MAX_TIME_SECONDS = 60
SOLVER_DEFAULT_K_BEST = 3
SOLVER_MAX_K_BEST = 8
