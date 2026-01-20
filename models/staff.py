# models/staff.py
"""Staff 모델"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Staff:
    """스태프 모델"""
    id: Optional[str] = None
    branch_id: Optional[str] = None
    name: str = ""
    gender: str = "M"  # 'M'|'F'
    role: str = "staff"  # 'manager'|'staff'
    target_off: int = 8  # 목표 휴일 수
    nenkyu: int = 0  # 연차 수
    skills: List[str] = field(default_factory=list)  # ['L1', 'NIGHT']
    prefer: str = ""  # 선호 정보
    display_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Staff":
        """딕셔너리에서 Staff 생성"""
        skills = data.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        return cls(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            name=data.get("name", ""),
            gender=data.get("gender", "M"),
            role=data.get("role", "staff"),
            target_off=data.get("target_off", 8),
            nenkyu=data.get("nenkyu", 0),
            skills=skills,
            prefer=data.get("prefer", ""),
            display_order=data.get("display_order", 0),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "name": self.name,
            "gender": self.gender,
            "role": self.role,
            "target_off": self.target_off,
            "nenkyu": self.nenkyu,
            "skills": ",".join(self.skills) if self.skills else "",
            "prefer": self.prefer,
            "display_order": self.display_order,
            "is_active": self.is_active,
        }
        if self.id:
            result["id"] = self.id
        if self.branch_id:
            result["branch_id"] = self.branch_id
        return result

    def has_skill(self, skill: str) -> bool:
        """특정 스킬 보유 여부"""
        return skill in self.skills

    def can_work_night(self) -> bool:
        """야간 근무 가능 여부"""
        return "NIGHT" in self.skills

    def can_work_l1(self) -> bool:
        """L1 근무 가능 여부"""
        return "L1" in self.skills

    def is_manager(self) -> bool:
        """매니저 여부"""
        return self.role == "manager"

    def get_skills_display(self) -> str:
        """스킬 표시용 문자열"""
        return ", ".join(self.skills) if self.skills else "-"


def get_staff_for_branch(branch_id: str, include_inactive: bool = False) -> List[Staff]:
    """지점의 스태프 목록 조회"""
    from core.database import get_db, is_demo_mode
    from core.session import get_demo_data

    if is_demo_mode():
        demo_staff = get_demo_data("staff_data")
        staff_list = [Staff.from_dict(s) for s in demo_staff]
        if not include_inactive:
            staff_list = [s for s in staff_list if s.is_active]
        return sorted(staff_list, key=lambda x: x.display_order)

    db = get_db()
    if db is None:
        return []

    try:
        query = db.table("staff").select("*").eq("branch_id", branch_id)
        if not include_inactive:
            query = query.eq("is_active", True)
        query = query.order("display_order")

        result = query.execute()
        return [Staff.from_dict(s) for s in result.data] if result.data else []

    except Exception:
        return []


def get_staff_by_skill(branch_id: str, skill: str) -> List[Staff]:
    """특정 스킬을 가진 스태프 조회"""
    all_staff = get_staff_for_branch(branch_id)
    return [s for s in all_staff if s.has_skill(skill)]


def get_night_capable_staff(branch_id: str) -> List[Staff]:
    """야간 근무 가능한 스태프"""
    return get_staff_by_skill(branch_id, "NIGHT")


def get_l1_capable_staff(branch_id: str) -> List[Staff]:
    """L1 근무 가능한 스태프"""
    return get_staff_by_skill(branch_id, "L1")


def get_staff_count(branch_id: str) -> Dict[str, int]:
    """스태프 통계"""
    all_staff = get_staff_for_branch(branch_id)

    return {
        "total": len(all_staff),
        "managers": len([s for s in all_staff if s.is_manager()]),
        "staff": len([s for s in all_staff if not s.is_manager()]),
        "male": len([s for s in all_staff if s.gender == "M"]),
        "female": len([s for s in all_staff if s.gender == "F"]),
        "night_capable": len([s for s in all_staff if s.can_work_night()]),
        "l1_capable": len([s for s in all_staff if s.can_work_l1()]),
    }
