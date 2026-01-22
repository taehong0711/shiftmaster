# config/default_constraints.py
"""기본 제약 조건 정의"""

DEFAULT_CONSTRAINTS = [
    # === HARD CONSTRAINTS (하드 제약) ===
    {
        "name": "night_after_night_off",
        "code": "NIGHT_AFTER_OFF",
        "category": "sequence",
        "constraint_type": "hard",
        "is_enabled": True,
        "penalty_weight": 200000,
        "priority_order": 1,
        "rule_definition": {
            "type": "sequence",
            "description_ja": "夜勤後は必ず明け休み",
            "description_ko": "야간 근무 후 반드시 휴무",
            "description_en": "Off day required after night shift",
            "rule": {
                "after_shifts": ["Q1", "X1", "R1"],
                "next_day_must_be": ["-"],
            }
        }
    },
    {
        "name": "max_consecutive_work",
        "code": "MAX_CONSEC_WORK",
        "category": "sequence",
        "constraint_type": "hard",
        "is_enabled": True,
        "penalty_weight": 200000,
        "priority_order": 2,
        "rule_definition": {
            "type": "rolling_window",
            "description_ja": "連続勤務は最大5日",
            "description_ko": "연속 근무 최대 5일",
            "description_en": "Maximum 5 consecutive work days",
            "rule": {
                "max_consecutive_work_days": 5,
            }
        }
    },
    {
        "name": "one_shift_per_day",
        "code": "ONE_SHIFT_DAY",
        "category": "coverage",
        "constraint_type": "hard",
        "is_enabled": True,
        "penalty_weight": 200000,
        "priority_order": 3,
        "rule_definition": {
            "type": "basic",
            "description_ja": "1日1シフトのみ",
            "description_ko": "하루 1시프트만",
            "description_en": "One shift per day only",
            "rule": {
                "exactly_one_shift_per_day": True,
            }
        }
    },
    {
        "name": "skill_required",
        "code": "SKILL_REQ",
        "category": "skill",
        "constraint_type": "hard",
        "is_enabled": True,
        "penalty_weight": 200000,
        "priority_order": 4,
        "rule_definition": {
            "type": "skill_match",
            "description_ja": "スキル要件を満たす必要あり",
            "description_ko": "스킬 요건 충족 필수",
            "description_en": "Skill requirements must be met",
            "rule": {
                "shift_skill_map": {
                    "L1": "L1",
                    "Q1": "NIGHT",
                    "X1": "NIGHT",
                    "R1": "NIGHT",
                }
            }
        }
    },
    {
        "name": "ng_shifts_forbidden",
        "code": "NG_FORBIDDEN",
        "category": "preference",
        "constraint_type": "hard",
        "is_enabled": True,
        "penalty_weight": 200000,
        "priority_order": 5,
        "rule_definition": {
            "type": "forbidden",
            "description_ja": "NG指定シフトは割り当て禁止",
            "description_ko": "NG 지정 시프트 배정 금지",
            "description_en": "NG designated shifts are forbidden",
            "rule": {
                "respect_ng_assignments": True,
            }
        }
    },

    # === SOFT CONSTRAINTS (소프트 제약) ===
    {
        "name": "request_satisfaction",
        "code": "REQ_SATISFY",
        "category": "preference",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 50000,
        "priority_order": 10,
        "rule_definition": {
            "type": "preference",
            "description_ja": "希望シフトをなるべく満たす",
            "description_ko": "희망 시프트 최대한 충족",
            "description_en": "Satisfy shift requests as much as possible",
            "rule": {
                "maximize_request_satisfaction": True,
            }
        }
    },
    {
        "name": "target_off_days",
        "code": "TARGET_OFF",
        "category": "balance",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 30000,
        "priority_order": 11,
        "rule_definition": {
            "type": "balance",
            "description_ja": "目標休日数に近づける",
            "description_ko": "목표 휴일 수 달성",
            "description_en": "Achieve target off days",
            "rule": {
                "target_off_days_field": "target_off",
                "deviation_penalty": True,
            }
        }
    },
    {
        "name": "night_shift_balance",
        "code": "NIGHT_BALANCE",
        "category": "balance",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 20000,
        "priority_order": 12,
        "rule_definition": {
            "type": "balance",
            "description_ja": "夜勤を均等に配分",
            "description_ko": "야간 근무 균등 배분",
            "description_en": "Balance night shifts among staff",
            "rule": {
                "balance_shifts": ["Q1", "X1", "R1"],
                "among_staff_with_skill": "NIGHT",
            }
        }
    },
    {
        "name": "min_daily_coverage",
        "code": "MIN_COVERAGE",
        "category": "coverage",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 40000,
        "priority_order": 13,
        "rule_definition": {
            "type": "coverage",
            "description_ja": "日別最低人数を確保",
            "description_ko": "일별 최소 인원 확보",
            "description_en": "Ensure minimum daily coverage",
            "rule": {
                "min_staff_per_day": 3,
                "exclude_shifts": ["-", "公"],
            }
        }
    },
    {
        "name": "weekend_balance",
        "code": "WEEKEND_BALANCE",
        "category": "balance",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 15000,
        "priority_order": 14,
        "rule_definition": {
            "type": "balance",
            "description_ja": "週末勤務を均等に",
            "description_ko": "주말 근무 균등 배분",
            "description_en": "Balance weekend work",
            "rule": {
                "balance_weekend_work": True,
            }
        }
    },
    {
        "name": "l1_daily_coverage",
        "code": "L1_COVERAGE",
        "category": "coverage",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 35000,
        "priority_order": 15,
        "rule_definition": {
            "type": "coverage",
            "description_ja": "毎日L1を1人配置",
            "description_ko": "매일 L1 1명 배치",
            "description_en": "One L1 shift per day",
            "rule": {
                "shift_code": "L1",
                "exactly_per_day": 1,
            }
        }
    },
    {
        "name": "avoid_split_weekends",
        "code": "AVOID_SPLIT_WEEKEND",
        "category": "preference",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 10000,
        "priority_order": 16,
        "rule_definition": {
            "type": "preference",
            "description_ja": "土日の片方だけ勤務を避ける",
            "description_ko": "주말 분할 근무 회피",
            "description_en": "Avoid working only one weekend day",
            "rule": {
                "prefer_full_weekend_off_or_work": True,
            }
        }
    },
    {
        "name": "closed_day_night_count",
        "code": "CLOSED_NIGHT",
        "category": "coverage",
        "constraint_type": "soft",
        "is_enabled": True,
        "penalty_weight": 25000,
        "priority_order": 17,
        "rule_definition": {
            "type": "coverage",
            "description_ja": "休館日の夜勤人数",
            "description_ko": "휴관일 야간 인원",
            "description_en": "Night shift count on closed days",
            "rule": {
                "on_closed_days": True,
                "night_shift_count": 2,
            }
        }
    },
]


# 제약 규칙 타입 정의 (직접 입력 모드에서 사용)
CONSTRAINT_RULE_TYPES = {
    "sequence": {
        "name_ja": "シーケンス",
        "name_ko": "시퀀스",
        "name_en": "Sequence",
        "description_ko": "특정 시프트 후 다음날 시프트 지정",
        "params": [
            {"key": "after_shifts", "label_ko": "선행 시프트 (쉼표 구분)", "type": "text", "default": "Q1,X1,R1"},
            {"key": "next_day_must_be", "label_ko": "다음날 시프트", "type": "text", "default": "-"},
        ]
    },
    "rolling_window": {
        "name_ja": "ローリングウィンドウ",
        "name_ko": "롤링 윈도우",
        "name_en": "Rolling Window",
        "description_ko": "연속 근무 일수 제한",
        "params": [
            {"key": "max_consecutive_work_days", "label_ko": "최대 연속 근무일", "type": "number", "default": 5, "min": 1, "max": 14},
        ]
    },
    "basic": {
        "name_ja": "基本",
        "name_ko": "기본",
        "name_en": "Basic",
        "description_ko": "기본 규칙 (하루 1시프트 등)",
        "params": [
            {"key": "exactly_one_shift_per_day", "label_ko": "하루 1시프트만", "type": "bool", "default": True},
        ]
    },
    "skill_match": {
        "name_ja": "スキルマッチ",
        "name_ko": "스킬 매칭",
        "name_en": "Skill Match",
        "description_ko": "시프트별 필요 스킬 지정",
        "params": [
            {"key": "shift_skill_map", "label_ko": "시프트-스킬 매핑 (JSON)", "type": "json", "default": '{"L1": "L1", "Q1": "NIGHT"}'},
        ]
    },
    "forbidden": {
        "name_ja": "禁止",
        "name_ko": "금지",
        "name_en": "Forbidden",
        "description_ko": "NG 지정 시프트 배정 금지",
        "params": [
            {"key": "respect_ng_assignments", "label_ko": "NG 지정 존중", "type": "bool", "default": True},
        ]
    },
    "preference": {
        "name_ja": "希望",
        "name_ko": "선호",
        "name_en": "Preference",
        "description_ko": "희망 시프트 반영",
        "params": [
            {"key": "maximize_request_satisfaction", "label_ko": "희망 충족 최대화", "type": "bool", "default": True},
            {"key": "prefer_full_weekend_off_or_work", "label_ko": "주말 분할 회피", "type": "bool", "default": False},
        ]
    },
    "balance": {
        "name_ja": "バランス",
        "name_ko": "균형",
        "name_en": "Balance",
        "description_ko": "근무 균등 배분",
        "params": [
            {"key": "balance_shifts", "label_ko": "균형 대상 시프트 (쉼표 구분)", "type": "text", "default": "Q1,X1,R1"},
            {"key": "among_staff_with_skill", "label_ko": "대상 스킬", "type": "text", "default": ""},
            {"key": "balance_weekend_work", "label_ko": "주말 균등 배분", "type": "bool", "default": False},
        ]
    },
    "coverage": {
        "name_ja": "カバレッジ",
        "name_ko": "커버리지",
        "name_en": "Coverage",
        "description_ko": "인원 배치 규칙",
        "params": [
            {"key": "min_staff_per_day", "label_ko": "일별 최소 인원", "type": "number", "default": 3, "min": 0, "max": 50},
            {"key": "shift_code", "label_ko": "대상 시프트 코드", "type": "text", "default": ""},
            {"key": "exactly_per_day", "label_ko": "일별 정확히 N명", "type": "number", "default": 0, "min": 0, "max": 50},
        ]
    },
}

# 추가 가능한 제약 템플릿 목록 (드롭다운 선택용)
AVAILABLE_CONSTRAINT_TEMPLATES = [
    {
        "template_id": "night_after_off",
        "name_ko": "야간 근무 후 휴무",
        "name_ja": "夜勤後の休み",
        "description_ko": "야간 시프트 다음날 반드시 휴무",
        "category": "sequence",
        "constraint_type": "hard",
        "default_weight": 200000,
        "rule_definition": {
            "type": "sequence",
            "rule": {"after_shifts": ["Q1", "X1", "R1"], "next_day_must_be": ["-"]}
        },
        "editable_params": [
            {"key": "after_shifts", "label_ko": "야간 시프트 코드", "type": "text", "default": "Q1,X1,R1"}
        ]
    },
    {
        "template_id": "max_consecutive_work",
        "name_ko": "연속 근무 제한",
        "name_ja": "連続勤務制限",
        "description_ko": "최대 연속 근무 일수 제한",
        "category": "sequence",
        "constraint_type": "hard",
        "default_weight": 200000,
        "rule_definition": {
            "type": "rolling_window",
            "rule": {"max_consecutive_work_days": 5}
        },
        "editable_params": [
            {"key": "max_consecutive_work_days", "label_ko": "최대 연속 일수", "type": "number", "default": 5, "min": 1, "max": 14}
        ]
    },
    {
        "template_id": "one_shift_per_day",
        "name_ko": "하루 1시프트",
        "name_ja": "1日1シフト",
        "description_ko": "하루에 하나의 시프트만 배정",
        "category": "coverage",
        "constraint_type": "hard",
        "default_weight": 200000,
        "rule_definition": {
            "type": "basic",
            "rule": {"exactly_one_shift_per_day": True}
        },
        "editable_params": []
    },
    {
        "template_id": "skill_required",
        "name_ko": "스킬 요건 충족",
        "name_ja": "スキル要件",
        "description_ko": "시프트별 필요 스킬 충족",
        "category": "skill",
        "constraint_type": "hard",
        "default_weight": 200000,
        "rule_definition": {
            "type": "skill_match",
            "rule": {"shift_skill_map": {"L1": "L1", "Q1": "NIGHT", "X1": "NIGHT", "R1": "NIGHT"}}
        },
        "editable_params": []
    },
    {
        "template_id": "ng_forbidden",
        "name_ko": "NG 시프트 금지",
        "name_ja": "NGシフト禁止",
        "description_ko": "NG 지정된 시프트 배정 금지",
        "category": "preference",
        "constraint_type": "hard",
        "default_weight": 200000,
        "rule_definition": {
            "type": "forbidden",
            "rule": {"respect_ng_assignments": True}
        },
        "editable_params": []
    },
    {
        "template_id": "request_satisfaction",
        "name_ko": "희망 시프트 충족",
        "name_ja": "希望シフト満足",
        "description_ko": "희망 시프트 최대한 반영",
        "category": "preference",
        "constraint_type": "soft",
        "default_weight": 50000,
        "rule_definition": {
            "type": "preference",
            "rule": {"maximize_request_satisfaction": True}
        },
        "editable_params": [
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 50000, "min": 0, "max": 200000}
        ]
    },
    {
        "template_id": "target_off_days",
        "name_ko": "목표 휴일 수 달성",
        "name_ja": "目標休日数",
        "description_ko": "직원별 목표 휴일 수 달성",
        "category": "balance",
        "constraint_type": "soft",
        "default_weight": 30000,
        "rule_definition": {
            "type": "balance",
            "rule": {"target_off_days_field": "target_off", "deviation_penalty": True}
        },
        "editable_params": [
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 30000, "min": 0, "max": 200000}
        ]
    },
    {
        "template_id": "night_balance",
        "name_ko": "야간 근무 균등 배분",
        "name_ja": "夜勤均等配分",
        "description_ko": "야간 근무를 직원들에게 균등하게 배분",
        "category": "balance",
        "constraint_type": "soft",
        "default_weight": 20000,
        "rule_definition": {
            "type": "balance",
            "rule": {"balance_shifts": ["Q1", "X1", "R1"], "among_staff_with_skill": "NIGHT"}
        },
        "editable_params": [
            {"key": "balance_shifts", "label_ko": "대상 시프트", "type": "text", "default": "Q1,X1,R1"},
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 20000, "min": 0, "max": 200000}
        ]
    },
    {
        "template_id": "min_coverage",
        "name_ko": "일별 최소 인원",
        "name_ja": "日別最低人数",
        "description_ko": "일별 최소 근무 인원 확보",
        "category": "coverage",
        "constraint_type": "soft",
        "default_weight": 40000,
        "rule_definition": {
            "type": "coverage",
            "rule": {"min_staff_per_day": 3, "exclude_shifts": ["-", "公"]}
        },
        "editable_params": [
            {"key": "min_staff_per_day", "label_ko": "최소 인원", "type": "number", "default": 3, "min": 1, "max": 50},
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 40000, "min": 0, "max": 200000}
        ]
    },
    {
        "template_id": "weekend_balance",
        "name_ko": "주말 근무 균등 배분",
        "name_ja": "週末勤務均等",
        "description_ko": "주말 근무를 직원들에게 균등하게 배분",
        "category": "balance",
        "constraint_type": "soft",
        "default_weight": 15000,
        "rule_definition": {
            "type": "balance",
            "rule": {"balance_weekend_work": True}
        },
        "editable_params": [
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 15000, "min": 0, "max": 200000}
        ]
    },
    {
        "template_id": "shift_coverage",
        "name_ko": "특정 시프트 일별 인원",
        "name_ja": "シフト別人数",
        "description_ko": "특정 시프트를 매일 정확히 N명 배치",
        "category": "coverage",
        "constraint_type": "soft",
        "default_weight": 35000,
        "rule_definition": {
            "type": "coverage",
            "rule": {"shift_code": "L1", "exactly_per_day": 1}
        },
        "editable_params": [
            {"key": "shift_code", "label_ko": "시프트 코드", "type": "text", "default": "L1"},
            {"key": "exactly_per_day", "label_ko": "일별 인원", "type": "number", "default": 1, "min": 0, "max": 50},
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 35000, "min": 0, "max": 200000}
        ]
    },
    {
        "template_id": "avoid_split_weekend",
        "name_ko": "주말 분할 근무 회피",
        "name_ja": "週末分割回避",
        "description_ko": "토일 중 하루만 근무하는 것을 회피",
        "category": "preference",
        "constraint_type": "soft",
        "default_weight": 10000,
        "rule_definition": {
            "type": "preference",
            "rule": {"prefer_full_weekend_off_or_work": True}
        },
        "editable_params": [
            {"key": "penalty_weight", "label_ko": "가중치", "type": "number", "default": 10000, "min": 0, "max": 200000}
        ]
    },
]


# 프리셋 정의
CONSTRAINT_PRESETS = {
    "strict": {
        "name_ja": "厳格モード",
        "name_ko": "엄격 모드",
        "name_en": "Strict Mode",
        "description_ja": "すべての制約を最大の重みで適用",
        "description_ko": "모든 제약을 최대 가중치로 적용",
        "description_en": "Apply all constraints with maximum weight",
        "weight_multiplier": 2.0,
    },
    "normal": {
        "name_ja": "通常モード",
        "name_ko": "보통 모드",
        "name_en": "Normal Mode",
        "description_ja": "標準の制約重み",
        "description_ko": "표준 제약 가중치",
        "description_en": "Standard constraint weights",
        "weight_multiplier": 1.0,
    },
    "flexible": {
        "name_ja": "柔軟モード",
        "name_ko": "유연 모드",
        "name_en": "Flexible Mode",
        "description_ja": "ソフト制約の重みを軽減",
        "description_ko": "소프트 제약 가중치 경감",
        "description_en": "Reduce soft constraint weights",
        "weight_multiplier": 0.5,
    },
}
