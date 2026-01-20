# models/shift.py
"""Shift 모델"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class MonthlyShift:
    """월별 시프트 모델"""
    id: Optional[str] = None
    branch_id: Optional[str] = None
    year: int = 0
    month: int = 0
    staff_name: str = ""
    shift_data: Dict[str, str] = field(default_factory=dict)  # {"1": "Q1", "2": "-", ...}
    off_days: int = 0
    work_days: int = 0
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MonthlyShift":
        """딕셔너리에서 MonthlyShift 생성"""
        return cls(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            year=data.get("year", 0),
            month=data.get("month", 0),
            staff_name=data.get("staff_name", ""),
            shift_data=data.get("shift_data", {}),
            off_days=data.get("off_days", 0),
            work_days=data.get("work_days", 0),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "year": self.year,
            "month": self.month,
            "staff_name": self.staff_name,
            "shift_data": self.shift_data,
            "off_days": self.off_days,
            "work_days": self.work_days,
            "created_by": self.created_by,
        }
        if self.id:
            result["id"] = self.id
        if self.branch_id:
            result["branch_id"] = self.branch_id
        return result

    def get_shift(self, day: int) -> str:
        """특정 날짜의 시프트 반환"""
        return self.shift_data.get(str(day), "")

    def set_shift(self, day: int, shift_code: str):
        """특정 날짜의 시프트 설정"""
        self.shift_data[str(day)] = shift_code


@dataclass
class MonthlyShiftSummary:
    """월별 시프트 요약 모델"""
    id: Optional[str] = None
    branch_id: Optional[str] = None
    year: int = 0
    month: int = 0
    summary_data: Dict[str, Any] = field(default_factory=dict)
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MonthlyShiftSummary":
        """딕셔너리에서 MonthlyShiftSummary 생성"""
        return cls(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            year=data.get("year", 0),
            month=data.get("month", 0),
            summary_data=data.get("summary_data", {}),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "year": self.year,
            "month": self.month,
            "summary_data": self.summary_data,
            "created_by": self.created_by,
        }
        if self.id:
            result["id"] = self.id
        if self.branch_id:
            result["branch_id"] = self.branch_id
        return result


@dataclass
class SwapRequest:
    """시프트 교환 요청 모델"""
    id: Optional[str] = None
    branch_id: Optional[str] = None
    requester: str = ""
    target: str = ""
    swap_date: str = ""  # YYYY-MM-DD
    requester_shift: str = ""
    target_shift: str = ""
    reason: str = ""
    status: str = "pending"  # 'pending'|'approved'|'rejected'
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SwapRequest":
        """딕셔너리에서 SwapRequest 생성"""
        return cls(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            requester=data.get("requester", ""),
            target=data.get("target", ""),
            swap_date=data.get("swap_date", ""),
            requester_shift=data.get("requester_shift", ""),
            target_shift=data.get("target_shift", ""),
            reason=data.get("reason", ""),
            status=data.get("status", "pending"),
            approved_by=data.get("approved_by"),
            approved_at=data.get("approved_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "requester": self.requester,
            "target": self.target,
            "swap_date": self.swap_date,
            "requester_shift": self.requester_shift,
            "target_shift": self.target_shift,
            "reason": self.reason,
            "status": self.status,
        }
        if self.id:
            result["id"] = self.id
        if self.branch_id:
            result["branch_id"] = self.branch_id
        if self.approved_by:
            result["approved_by"] = self.approved_by
        if self.approved_at:
            result["approved_at"] = str(self.approved_at)
        return result

    def is_pending(self) -> bool:
        """대기 중 여부"""
        return self.status == "pending"

    def is_approved(self) -> bool:
        """승인 여부"""
        return self.status == "approved"

    def is_rejected(self) -> bool:
        """거절 여부"""
        return self.status == "rejected"


@dataclass
class Notification:
    """알림 모델"""
    id: Optional[str] = None
    branch_id: Optional[str] = None
    user_id: str = ""
    title: str = ""
    message: str = ""
    type: str = "info"  # 'info'|'success'|'warning'|'error'|'swap'
    read: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Notification":
        """딕셔너리에서 Notification 생성"""
        return cls(
            id=data.get("id"),
            branch_id=data.get("branch_id"),
            user_id=data.get("user_id", ""),
            title=data.get("title", ""),
            message=data.get("message", ""),
            type=data.get("type", "info"),
            read=data.get("read", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        result = {
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "read": self.read,
        }
        if self.id:
            result["id"] = self.id
        if self.branch_id:
            result["branch_id"] = self.branch_id
        return result


def get_monthly_shifts(branch_id: str, year: int, month: int) -> List[MonthlyShift]:
    """월별 시프트 조회"""
    from core.database import get_db, is_demo_mode
    from core.session import get_demo_data

    if is_demo_mode():
        demo_shifts = get_demo_data("monthly_shifts")
        return [
            MonthlyShift.from_dict(s) for s in demo_shifts
            if s.get("year") == year and s.get("month") == month
        ]

    db = get_db()
    if db is None:
        return []

    try:
        result = db.table("monthly_shifts").select("*").eq(
            "branch_id", branch_id
        ).eq("year", year).eq("month", month).execute()

        return [MonthlyShift.from_dict(s) for s in result.data] if result.data else []

    except Exception:
        return []


def get_saved_months(branch_id: str) -> List[tuple]:
    """저장된 월 목록 조회"""
    from core.database import get_db, is_demo_mode
    from core.session import get_demo_data

    if is_demo_mode():
        demo_shifts = get_demo_data("monthly_shifts")
        months = set()
        for s in demo_shifts:
            months.add((s.get("year"), s.get("month")))
        return sorted(list(months), reverse=True)

    db = get_db()
    if db is None:
        return []

    try:
        result = db.table("monthly_shifts").select(
            "year, month"
        ).eq("branch_id", branch_id).execute()

        if result.data:
            months = set()
            for s in result.data:
                months.add((s.get("year"), s.get("month")))
            return sorted(list(months), reverse=True)
        return []

    except Exception:
        return []
