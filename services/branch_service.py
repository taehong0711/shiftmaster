# services/branch_service.py
"""지점 서비스"""

import streamlit as st
from typing import Optional, List, Dict
from models.branch import Branch, UserBranch
from core.database import get_db, is_demo_mode, db_insert, db_update, db_delete, db_select
from core.session import get_demo_data, set_demo_data, add_demo_data, delete_demo_data
from config.constants import DEFAULT_DAY_SHIFTS, DEFAULT_NIGHT_SHIFTS
import uuid


class BranchService:
    """지점 관리 서비스"""

    @staticmethod
    def get_all_branches(active_only: bool = True) -> List[Branch]:
        """모든 지점 조회"""
        if is_demo_mode():
            branches = get_demo_data("branches")
            if active_only:
                branches = [b for b in branches if b.get("is_active", True)]
            return [Branch.from_dict(b) for b in branches]

        db = get_db()
        if db is None:
            return []

        try:
            query = db.table("branches").select("*")
            if active_only:
                query = query.eq("is_active", True)
            result = query.order("name").execute()
            return [Branch.from_dict(b) for b in result.data] if result.data else []
        except Exception as e:
            st.error(f"지점 조회 오류: {e}")
            return []

    @staticmethod
    def get_branch_by_id(branch_id: str) -> Optional[Branch]:
        """ID로 지점 조회"""
        if is_demo_mode():
            branches = get_demo_data("branches")
            for b in branches:
                if b.get("id") == branch_id:
                    return Branch.from_dict(b)
            return None

        db = get_db()
        if db is None:
            return None

        try:
            result = db.table("branches").select("*").eq("id", branch_id).limit(1).execute()
            if result.data:
                return Branch.from_dict(result.data[0])
            return None
        except Exception:
            return None

    @staticmethod
    def get_branch_by_code(code: str) -> Optional[Branch]:
        """코드로 지점 조회"""
        if is_demo_mode():
            branches = get_demo_data("branches")
            for b in branches:
                if b.get("code") == code:
                    return Branch.from_dict(b)
            return None

        db = get_db()
        if db is None:
            return None

        try:
            result = db.table("branches").select("*").eq("code", code).limit(1).execute()
            if result.data:
                return Branch.from_dict(result.data[0])
            return None
        except Exception:
            return None

    @staticmethod
    def create_branch(name: str, code: str, timezone: str = "Asia/Tokyo", settings: dict = None) -> Optional[Branch]:
        """지점 생성"""
        data = {
            "name": name,
            "code": code,
            "timezone": timezone,
            "is_active": True,
            "settings": settings or {},
        }

        if is_demo_mode():
            data["id"] = str(uuid.uuid4())
            add_demo_data("branches", data)
            return Branch.from_dict(data)

        result = db_insert("branches", data)
        if result:
            return Branch.from_dict(result)
        return None

    @staticmethod
    def update_branch(branch_id: str, **kwargs) -> bool:
        """지점 정보 업데이트"""
        if is_demo_mode():
            branches = get_demo_data("branches")
            for i, b in enumerate(branches):
                if b.get("id") == branch_id:
                    b.update(kwargs)
                    branches[i] = b
                    set_demo_data("branches", branches)
                    return True
            return False

        result = db_update("branches", {"id": branch_id}, kwargs)
        return result is not None

    @staticmethod
    def delete_branch(branch_id: str) -> bool:
        """지점 삭제 (비활성화)"""
        return BranchService.update_branch(branch_id, is_active=False)

    @staticmethod
    def hard_delete_branch(branch_id: str) -> bool:
        """지점 완전 삭제"""
        if is_demo_mode():
            delete_demo_data("branches", "id", branch_id)
            return True

        return db_delete("branches", {"id": branch_id})

    @staticmethod
    def get_user_branches(user_id: str) -> List[Branch]:
        """사용자가 접근 가능한 지점 목록"""
        if is_demo_mode():
            # 데모 모드에서는 모든 지점 반환
            return BranchService.get_all_branches()

        db = get_db()
        if db is None:
            return []

        try:
            result = db.table("user_branches").select(
                "branch_id, role, is_primary, branches(*)"
            ).eq("user_id", user_id).execute()

            branches = []
            if result.data:
                for item in result.data:
                    if item.get("branches"):
                        branches.append(Branch.from_dict(item["branches"]))
            return branches
        except Exception:
            return []

    @staticmethod
    def assign_user_to_branch(user_id: str, branch_id: str, role: str = "viewer", is_primary: bool = False) -> bool:
        """사용자를 지점에 할당"""
        data = {
            "user_id": user_id,
            "branch_id": branch_id,
            "role": role,
            "is_primary": is_primary,
        }

        if is_demo_mode():
            data["id"] = str(uuid.uuid4())
            add_demo_data("user_branches", data)
            return True

        db = get_db()
        if db is None:
            return False

        try:
            db.table("user_branches").upsert(
                data, on_conflict="user_id,branch_id"
            ).execute()
            return True
        except Exception as e:
            st.error(f"지점 할당 오류: {e}")
            return False

    @staticmethod
    def remove_user_from_branch(user_id: str, branch_id: str) -> bool:
        """사용자를 지점에서 제거"""
        if is_demo_mode():
            user_branches = get_demo_data("user_branches")
            user_branches = [
                ub for ub in user_branches
                if not (ub.get("user_id") == user_id and ub.get("branch_id") == branch_id)
            ]
            set_demo_data("user_branches", user_branches)
            return True

        return db_delete("user_branches", {"user_id": user_id, "branch_id": branch_id})

    @staticmethod
    def get_user_role_in_branch(user_id: str, branch_id: str) -> Optional[str]:
        """지점에서의 사용자 역할 조회"""
        if is_demo_mode():
            user_branches = get_demo_data("user_branches")
            for ub in user_branches:
                if ub.get("user_id") == user_id and ub.get("branch_id") == branch_id:
                    return ub.get("role")
            return None

        db = get_db()
        if db is None:
            return None

        try:
            result = db.table("user_branches").select("role").eq(
                "user_id", user_id
            ).eq("branch_id", branch_id).limit(1).execute()

            if result.data:
                return result.data[0].get("role")
            return None
        except Exception:
            return None

    @staticmethod
    def set_primary_branch(user_id: str, branch_id: str) -> bool:
        """기본 지점 설정"""
        if is_demo_mode():
            user_branches = get_demo_data("user_branches")
            for ub in user_branches:
                if ub.get("user_id") == user_id:
                    ub["is_primary"] = (ub.get("branch_id") == branch_id)
            set_demo_data("user_branches", user_branches)
            return True

        db = get_db()
        if db is None:
            return False

        try:
            # 기존 primary 해제
            db.table("user_branches").update({"is_primary": False}).eq(
                "user_id", user_id
            ).execute()

            # 새 primary 설정
            db.table("user_branches").update({"is_primary": True}).eq(
                "user_id", user_id
            ).eq("branch_id", branch_id).execute()

            return True
        except Exception:
            return False

    @staticmethod
    def ensure_default_branch() -> Optional[Branch]:
        """기본 지점이 없으면 생성"""
        branches = BranchService.get_all_branches()
        if branches:
            return branches[0]

        # 기본 지점 생성 (기본 시프트 코드 포함)
        return BranchService.create_branch(
            name="本店",
            code="MAIN",
            timezone="Asia/Tokyo",
            settings={
                "is_default": True,
                "day_shifts": DEFAULT_DAY_SHIFTS.copy(),
                "night_shifts": DEFAULT_NIGHT_SHIFTS.copy()
            }
        )

    @staticmethod
    def get_branch_shift_codes(branch_id: str) -> Dict[str, List[str]]:
        """지점별 시프트 코드 조회"""
        branch = BranchService.get_branch_by_id(branch_id)
        if branch and branch.settings:
            day_shifts = branch.settings.get("day_shifts", DEFAULT_DAY_SHIFTS.copy())
            night_shifts = branch.settings.get("night_shifts", DEFAULT_NIGHT_SHIFTS.copy())
            required_shifts = branch.settings.get("required_shifts", [])
            return {
                "day_shifts": day_shifts,
                "night_shifts": night_shifts,
                "required_shifts": required_shifts
            }
        return {
            "day_shifts": DEFAULT_DAY_SHIFTS.copy(),
            "night_shifts": DEFAULT_NIGHT_SHIFTS.copy(),
            "required_shifts": []
        }

    @staticmethod
    def update_branch_shift_codes(branch_id: str, day_shifts: List[str], night_shifts: List[str], required_shifts: List[str] = None) -> bool:
        """지점별 시프트 코드 업데이트"""
        branch = BranchService.get_branch_by_id(branch_id)
        if not branch:
            return False

        # 기존 settings에 시프트 코드 업데이트
        settings = branch.settings or {}
        settings["day_shifts"] = day_shifts
        settings["night_shifts"] = night_shifts
        if required_shifts is not None:
            settings["required_shifts"] = required_shifts

        return BranchService.update_branch(branch_id, settings=settings)
