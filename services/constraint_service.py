# services/constraint_service.py
"""제약 조건 서비스"""

import streamlit as st
from typing import Optional, List, Dict, Any
from models.constraint import Constraint
from core.database import get_db, is_demo_mode, db_insert, db_update, db_delete
from core.session import get_demo_data, set_demo_data, add_demo_data, delete_demo_data
from config.default_constraints import DEFAULT_CONSTRAINTS, CONSTRAINT_PRESETS
import uuid
import json


class ConstraintService:
    """제약 조건 관리 서비스"""

    @staticmethod
    def get_all_constraints(branch_id: str) -> List[Constraint]:
        """지점의 모든 제약 조건 조회"""
        if is_demo_mode():
            constraints = get_demo_data("constraints")
            return [
                Constraint.from_dict(c) for c in constraints
                if c.get("branch_id") == branch_id
            ]

        db = get_db()
        if db is None:
            return []

        try:
            result = db.table("constraints").select("*").eq(
                "branch_id", branch_id
            ).order("priority_order").execute()
            return [Constraint.from_dict(c) for c in result.data] if result.data else []
        except Exception as e:
            st.error(f"제약 조건 조회 오류: {e}")
            return []

    @staticmethod
    def get_constraint_by_id(constraint_id: str) -> Optional[Constraint]:
        """ID로 제약 조건 조회"""
        if is_demo_mode():
            constraints = get_demo_data("constraints")
            for c in constraints:
                if c.get("id") == constraint_id:
                    return Constraint.from_dict(c)
            return None

        db = get_db()
        if db is None:
            return None

        try:
            result = db.table("constraints").select("*").eq(
                "id", constraint_id
            ).limit(1).execute()
            if result.data:
                return Constraint.from_dict(result.data[0])
            return None
        except Exception:
            return None

    @staticmethod
    def get_constraint_by_code(branch_id: str, code: str) -> Optional[Constraint]:
        """코드로 제약 조건 조회"""
        constraints = ConstraintService.get_all_constraints(branch_id)
        for c in constraints:
            if c.code == code:
                return c
        return None

    @staticmethod
    def create_constraint(branch_id: str, constraint_data: dict) -> Optional[Constraint]:
        """제약 조건 생성"""
        data = {
            "branch_id": branch_id,
            "name": constraint_data.get("name", ""),
            "code": constraint_data.get("code", ""),
            "category": constraint_data.get("category", "coverage"),
            "constraint_type": constraint_data.get("constraint_type", "soft"),
            "is_enabled": constraint_data.get("is_enabled", True),
            "penalty_weight": constraint_data.get("penalty_weight", 10000),
            "priority_order": constraint_data.get("priority_order", 50),
            "rule_definition": constraint_data.get("rule_definition", {}),
        }

        if is_demo_mode():
            data["id"] = str(uuid.uuid4())
            add_demo_data("constraints", data)
            return Constraint.from_dict(data)

        result = db_insert("constraints", data)
        if result:
            return Constraint.from_dict(result)
        return None

    @staticmethod
    def update_constraint(constraint_id: str, **kwargs) -> bool:
        """제약 조건 업데이트"""
        if is_demo_mode():
            constraints = get_demo_data("constraints")
            for i, c in enumerate(constraints):
                if c.get("id") == constraint_id:
                    c.update(kwargs)
                    constraints[i] = c
                    set_demo_data("constraints", constraints)
                    return True
            return False

        result = db_update("constraints", {"id": constraint_id}, kwargs)
        return result is not None

    @staticmethod
    def delete_constraint(constraint_id: str) -> bool:
        """제약 조건 삭제"""
        if is_demo_mode():
            delete_demo_data("constraints", "id", constraint_id)
            return True

        return db_delete("constraints", {"id": constraint_id})

    @staticmethod
    def toggle_constraint(constraint_id: str) -> bool:
        """제약 조건 활성화/비활성화 토글"""
        constraint = ConstraintService.get_constraint_by_id(constraint_id)
        if constraint:
            return ConstraintService.update_constraint(
                constraint_id, is_enabled=not constraint.is_enabled
            )
        return False

    @staticmethod
    def update_weight(constraint_id: str, weight: int) -> bool:
        """가중치 업데이트"""
        return ConstraintService.update_constraint(constraint_id, penalty_weight=weight)

    @staticmethod
    def update_priority(constraint_id: str, priority: int) -> bool:
        """우선순위 업데이트"""
        return ConstraintService.update_constraint(constraint_id, priority_order=priority)

    @staticmethod
    def reorder_constraints(branch_id: str, constraint_ids: List[str]) -> bool:
        """제약 조건 순서 재정렬"""
        try:
            for i, cid in enumerate(constraint_ids):
                ConstraintService.update_constraint(cid, priority_order=i + 1)
            return True
        except Exception:
            return False

    @staticmethod
    def get_enabled_constraints(branch_id: str) -> List[Constraint]:
        """활성화된 제약 조건만 조회"""
        all_constraints = ConstraintService.get_all_constraints(branch_id)
        return [c for c in all_constraints if c.is_enabled]

    @staticmethod
    def get_hard_constraints(branch_id: str) -> List[Constraint]:
        """하드 제약만 조회"""
        enabled = ConstraintService.get_enabled_constraints(branch_id)
        return [c for c in enabled if c.is_hard()]

    @staticmethod
    def get_soft_constraints(branch_id: str) -> List[Constraint]:
        """소프트 제약만 조회"""
        enabled = ConstraintService.get_enabled_constraints(branch_id)
        return [c for c in enabled if c.is_soft()]

    @staticmethod
    def get_constraints_by_category(branch_id: str, category: str) -> List[Constraint]:
        """카테고리별 제약 조회"""
        enabled = ConstraintService.get_enabled_constraints(branch_id)
        return [c for c in enabled if c.category == category]

    @staticmethod
    def init_default_constraints(branch_id: str) -> bool:
        """기본 제약 조건 초기화"""
        existing = ConstraintService.get_all_constraints(branch_id)
        if existing:
            return False  # 이미 존재하면 초기화 안함

        try:
            for constraint_def in DEFAULT_CONSTRAINTS:
                ConstraintService.create_constraint(branch_id, constraint_def)
            return True
        except Exception as e:
            st.error(f"기본 제약 초기화 오류: {e}")
            return False

    @staticmethod
    def apply_preset(branch_id: str, preset_name: str) -> bool:
        """프리셋 적용"""
        if preset_name not in CONSTRAINT_PRESETS:
            return False

        preset = CONSTRAINT_PRESETS[preset_name]
        multiplier = preset.get("weight_multiplier", 1.0)

        constraints = ConstraintService.get_all_constraints(branch_id)
        try:
            for c in constraints:
                if c.is_soft():
                    # 기본 가중치 가져오기
                    default = ConstraintService._get_default_weight(c.code)
                    new_weight = int(default * multiplier)
                    ConstraintService.update_weight(c.id, new_weight)
            return True
        except Exception:
            return False

    @staticmethod
    def _get_default_weight(code: str) -> int:
        """코드로 기본 가중치 조회"""
        for c in DEFAULT_CONSTRAINTS:
            if c.get("code") == code:
                return c.get("penalty_weight", 10000)
        return 10000

    @staticmethod
    def export_constraints(branch_id: str) -> str:
        """제약 조건을 JSON으로 내보내기"""
        constraints = ConstraintService.get_all_constraints(branch_id)
        data = [c.to_dict() for c in constraints]
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def import_constraints(branch_id: str, json_str: str, replace: bool = False) -> bool:
        """JSON에서 제약 조건 가져오기"""
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                return False

            if replace:
                # 기존 제약 삭제
                existing = ConstraintService.get_all_constraints(branch_id)
                for c in existing:
                    ConstraintService.delete_constraint(c.id)

            for item in data:
                # ID 제거 (새로 생성)
                if "id" in item:
                    del item["id"]
                ConstraintService.create_constraint(branch_id, item)

            return True
        except Exception as e:
            st.error(f"제약 조건 가져오기 오류: {e}")
            return False

    @staticmethod
    def get_constraints_summary(branch_id: str) -> Dict[str, Any]:
        """제약 조건 요약 정보"""
        all_constraints = ConstraintService.get_all_constraints(branch_id)
        enabled = [c for c in all_constraints if c.is_enabled]

        return {
            "total": len(all_constraints),
            "enabled": len(enabled),
            "disabled": len(all_constraints) - len(enabled),
            "hard": len([c for c in enabled if c.is_hard()]),
            "soft": len([c for c in enabled if c.is_soft()]),
            "by_category": {
                "coverage": len([c for c in enabled if c.category == "coverage"]),
                "sequence": len([c for c in enabled if c.category == "sequence"]),
                "balance": len([c for c in enabled if c.category == "balance"]),
                "preference": len([c for c in enabled if c.category == "preference"]),
                "skill": len([c for c in enabled if c.category == "skill"]),
            }
        }
