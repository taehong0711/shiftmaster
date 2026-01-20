# models/branch.py
"""Branch 모델"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Branch:
    """지점 모델"""
    id: Optional[str] = None
    name: str = ""
    code: str = ""  # 유니크 코드 (예: "TOKYO_MAIN")
    timezone: str = "Asia/Tokyo"
    is_active: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Branch":
        """딕셔너리에서 Branch 생성"""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            code=data.get("code", ""),
            timezone=data.get("timezone", "Asia/Tokyo"),
            is_active=data.get("is_active", True),
            settings=data.get("settings", {}),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "name": self.name,
            "code": self.code,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "settings": self.settings,
        }
        if self.id:
            result["id"] = self.id
        return result


@dataclass
class UserBranch:
    """사용자-지점 관계 모델"""
    id: Optional[str] = None
    user_id: str = ""
    branch_id: str = ""
    role: str = "viewer"  # 'super'|'editor'|'viewer'
    is_primary: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "UserBranch":
        """딕셔너리에서 UserBranch 생성"""
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            branch_id=data.get("branch_id", ""),
            role=data.get("role", "viewer"),
            is_primary=data.get("is_primary", False),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "user_id": self.user_id,
            "branch_id": self.branch_id,
            "role": self.role,
            "is_primary": self.is_primary,
        }
        if self.id:
            result["id"] = self.id
        return result


def get_user_branches(user_id: str) -> List[Branch]:
    """사용자가 접근 가능한 지점 목록 조회"""
    from core.database import get_db, is_demo_mode
    from core.session import get_demo_data

    if is_demo_mode():
        # 데모 모드: 세션에서 지점 데이터 반환
        demo_branches = get_demo_data("branches")
        return [Branch.from_dict(b) for b in demo_branches]

    db = get_db()
    if db is None:
        return []

    try:
        # user_branches 조인하여 지점 목록 가져오기
        result = db.table("user_branches").select(
            "branch_id, role, is_primary, branches(*)"
        ).eq("user_id", user_id).execute()

        branches = []
        if result.data:
            for item in result.data:
                if item.get("branches"):
                    branch = Branch.from_dict(item["branches"])
                    branches.append(branch)
        return branches

    except Exception:
        return []


def get_primary_branch(user_id: str) -> Optional[Branch]:
    """사용자의 기본 지점 조회"""
    from core.database import get_db, is_demo_mode
    from core.session import get_demo_data

    if is_demo_mode():
        demo_branches = get_demo_data("branches")
        if demo_branches:
            return Branch.from_dict(demo_branches[0])
        return None

    db = get_db()
    if db is None:
        return None

    try:
        result = db.table("user_branches").select(
            "branches(*)"
        ).eq("user_id", user_id).eq("is_primary", True).limit(1).execute()

        if result.data and result.data[0].get("branches"):
            return Branch.from_dict(result.data[0]["branches"])

        # 기본 지점이 없으면 첫 번째 지점 반환
        result = db.table("user_branches").select(
            "branches(*)"
        ).eq("user_id", user_id).limit(1).execute()

        if result.data and result.data[0].get("branches"):
            return Branch.from_dict(result.data[0]["branches"])

        return None

    except Exception:
        return None
