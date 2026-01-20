# models/constraint.py
"""Constraint 모델"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Constraint:
    """제약 조건 모델"""
    id: Optional[str] = None
    branch_id: Optional[str] = None
    name: str = ""
    code: str = ""
    category: str = "coverage"  # 'coverage'|'sequence'|'balance'|'preference'|'skill'
    constraint_type: str = "soft"  # 'hard'|'soft'
    is_enabled: bool = True
    penalty_weight: int = 10000
    priority_order: int = 50
    rule_definition: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Constraint":
        """딕셔너리에서 Constraint 생성"""
        return cls(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            name=data.get("name", ""),
            code=data.get("code", ""),
            category=data.get("category", "coverage"),
            constraint_type=data.get("constraint_type", "soft"),
            is_enabled=data.get("is_enabled", True),
            penalty_weight=data.get("penalty_weight", 10000),
            priority_order=data.get("priority_order", 50),
            rule_definition=data.get("rule_definition", {}),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "name": self.name,
            "code": self.code,
            "category": self.category,
            "constraint_type": self.constraint_type,
            "is_enabled": self.is_enabled,
            "penalty_weight": self.penalty_weight,
            "priority_order": self.priority_order,
            "rule_definition": self.rule_definition,
        }
        if self.id:
            result["id"] = self.id
        if self.branch_id:
            result["branch_id"] = self.branch_id
        return result

    def is_hard(self) -> bool:
        """하드 제약 여부"""
        return self.constraint_type == "hard"

    def is_soft(self) -> bool:
        """소프트 제약 여부"""
        return self.constraint_type == "soft"

    def get_description(self, lang: str = "ja") -> str:
        """언어별 설명 반환"""
        desc_key = f"description_{lang}"
        return self.rule_definition.get(desc_key, self.name)

    def get_rule_type(self) -> str:
        """규칙 타입 반환"""
        return self.rule_definition.get("type", "basic")

    def get_rule(self) -> Dict[str, Any]:
        """규칙 정의 반환"""
        return self.rule_definition.get("rule", {})


def get_constraints_for_branch(branch_id: str) -> List[Constraint]:
    """지점의 제약 조건 목록 조회"""
    from core.database import get_db, is_demo_mode
    from core.session import get_demo_data

    if is_demo_mode():
        demo_constraints = get_demo_data("constraints")
        return [
            Constraint.from_dict(c) for c in demo_constraints
            if c.get("branch_id") == branch_id or c.get("branch_id") is None
        ]

    db = get_db()
    if db is None:
        return []

    try:
        result = db.table("constraints").select("*").eq(
            "branch_id", branch_id
        ).order("priority_order").execute()

        return [Constraint.from_dict(c) for c in result.data] if result.data else []

    except Exception:
        return []


def get_enabled_constraints(branch_id: str) -> List[Constraint]:
    """활성화된 제약 조건만 조회"""
    all_constraints = get_constraints_for_branch(branch_id)
    return [c for c in all_constraints if c.is_enabled]


def get_hard_constraints(branch_id: str) -> List[Constraint]:
    """하드 제약만 조회"""
    enabled = get_enabled_constraints(branch_id)
    return [c for c in enabled if c.is_hard()]


def get_soft_constraints(branch_id: str) -> List[Constraint]:
    """소프트 제약만 조회"""
    enabled = get_enabled_constraints(branch_id)
    return [c for c in enabled if c.is_soft()]


def get_constraints_by_category(branch_id: str, category: str) -> List[Constraint]:
    """카테고리별 제약 조회"""
    enabled = get_enabled_constraints(branch_id)
    return [c for c in enabled if c.category == category]
