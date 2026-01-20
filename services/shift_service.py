# services/shift_service.py
"""시프트 서비스"""

import streamlit as st
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
from models.shift import MonthlyShift, MonthlyShiftSummary, SwapRequest, Notification
from models.staff import Staff, get_staff_for_branch
from core.database import get_db, is_demo_mode, db_insert, db_update, db_delete, db_upsert
from core.session import get_demo_data, set_demo_data, add_demo_data, delete_demo_data
from core.auth import get_current_user
import uuid


class ShiftService:
    """시프트 관리 서비스"""

    # === 월별 시프트 ===

    @staticmethod
    def get_monthly_shifts(branch_id: str, year: int, month: int) -> List[MonthlyShift]:
        """월별 시프트 조회"""
        if is_demo_mode():
            demo_shifts = get_demo_data("monthly_shifts")
            if isinstance(demo_shifts, dict):
                # 구조: {(year, month): [{staff_name, shift_data, ...}, ...]}
                key = f"{year}-{month}"
                data = demo_shifts.get(key, [])
                return [MonthlyShift.from_dict(s) for s in data]
            return []

        db = get_db()
        if db is None:
            return []

        try:
            result = db.table("monthly_shifts").select("*").eq(
                "branch_id", branch_id
            ).eq("year", year).eq("month", month).execute()

            return [MonthlyShift.from_dict(s) for s in result.data] if result.data else []
        except Exception as e:
            st.error(f"시프트 조회 오류: {e}")
            return []

    @staticmethod
    def save_monthly_shifts(branch_id: str, year: int, month: int,
                           shifts_df: pd.DataFrame, summary_data: dict = None) -> bool:
        """월별 시프트 저장"""
        user = get_current_user() or "system"

        if is_demo_mode():
            demo_shifts = get_demo_data("monthly_shifts")
            if not isinstance(demo_shifts, dict):
                demo_shifts = {}

            key = f"{year}-{month}"
            demo_shifts[key] = []

            for _, row in shifts_df.iterrows():
                staff_name = row.get("name", row.get("スタッフ", ""))
                shift_data = {}
                off_days = 0
                work_days = 0

                for col in shifts_df.columns:
                    if col not in ["name", "スタッフ", "休日数", "勤務数", "出勤日数"]:
                        try:
                            day = int(col)
                            shift = str(row[col])
                            shift_data[str(day)] = shift
                            if shift in ["-", "公"]:
                                off_days += 1
                            elif shift and shift != "":
                                work_days += 1
                        except (ValueError, TypeError):
                            pass

                demo_shifts[key].append({
                    "id": str(uuid.uuid4()),
                    "branch_id": branch_id,
                    "year": year,
                    "month": month,
                    "staff_name": staff_name,
                    "shift_data": shift_data,
                    "off_days": off_days,
                    "work_days": work_days,
                    "created_by": user,
                })

            set_demo_data("monthly_shifts", demo_shifts)
            return True

        db = get_db()
        if db is None:
            return False

        try:
            # 기존 데이터 삭제
            db.table("monthly_shifts").delete().eq(
                "branch_id", branch_id
            ).eq("year", year).eq("month", month).execute()

            # 새 데이터 삽입
            for _, row in shifts_df.iterrows():
                staff_name = row.get("name", row.get("スタッフ", ""))
                shift_data = {}
                off_days = 0
                work_days = 0

                for col in shifts_df.columns:
                    if col not in ["name", "スタッフ", "休日数", "勤務数", "出勤日数"]:
                        try:
                            day = int(col)
                            shift = str(row[col])
                            shift_data[str(day)] = shift
                            if shift in ["-", "公"]:
                                off_days += 1
                            elif shift and shift != "":
                                work_days += 1
                        except (ValueError, TypeError):
                            pass

                db.table("monthly_shifts").insert({
                    "branch_id": branch_id,
                    "year": year,
                    "month": month,
                    "staff_name": staff_name,
                    "shift_data": shift_data,
                    "off_days": off_days,
                    "work_days": work_days,
                    "created_by": user,
                }).execute()

            # 요약 저장
            if summary_data:
                ShiftService.save_monthly_summary(branch_id, year, month, summary_data)

            return True
        except Exception as e:
            st.error(f"시프트 저장 오류: {e}")
            return False

    @staticmethod
    def delete_monthly_shifts(branch_id: str, year: int, month: int) -> bool:
        """월별 시프트 삭제"""
        if is_demo_mode():
            demo_shifts = get_demo_data("monthly_shifts")
            if isinstance(demo_shifts, dict):
                key = f"{year}-{month}"
                if key in demo_shifts:
                    del demo_shifts[key]
                    set_demo_data("monthly_shifts", demo_shifts)
            return True

        db = get_db()
        if db is None:
            return False

        try:
            db.table("monthly_shifts").delete().eq(
                "branch_id", branch_id
            ).eq("year", year).eq("month", month).execute()

            db.table("monthly_shifts_summary").delete().eq(
                "branch_id", branch_id
            ).eq("year", year).eq("month", month).execute()

            return True
        except Exception:
            return False

    @staticmethod
    def get_saved_months(branch_id: str) -> List[Tuple[int, int]]:
        """저장된 월 목록 조회"""
        if is_demo_mode():
            demo_shifts = get_demo_data("monthly_shifts")
            if isinstance(demo_shifts, dict):
                months = []
                for key in demo_shifts.keys():
                    parts = key.split("-")
                    if len(parts) == 2:
                        months.append((int(parts[0]), int(parts[1])))
                return sorted(months, reverse=True)
            return []

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

    @staticmethod
    def save_monthly_summary(branch_id: str, year: int, month: int, summary_data: dict) -> bool:
        """월별 요약 저장"""
        user = get_current_user() or "system"

        if is_demo_mode():
            return True  # 데모 모드에서는 별도 저장 안함

        db = get_db()
        if db is None:
            return False

        try:
            db.table("monthly_shifts_summary").upsert({
                "branch_id": branch_id,
                "year": year,
                "month": month,
                "summary_data": summary_data,
                "created_by": user,
            }, on_conflict="branch_id,year,month").execute()
            return True
        except Exception:
            return False

    # === 시프트 교환 ===

    @staticmethod
    def get_pending_swap_requests(branch_id: str) -> List[SwapRequest]:
        """대기 중인 교환 요청 조회"""
        if is_demo_mode():
            swaps = get_demo_data("swap_requests")
            return [
                SwapRequest.from_dict(s) for s in swaps
                if s.get("branch_id") == branch_id and s.get("status") == "pending"
            ]

        db = get_db()
        if db is None:
            return []

        try:
            result = db.table("swap_requests").select("*").eq(
                "branch_id", branch_id
            ).eq("status", "pending").order("created_at", desc=True).execute()

            return [SwapRequest.from_dict(s) for s in result.data] if result.data else []
        except Exception:
            return []

    @staticmethod
    def get_user_swap_requests(branch_id: str, user_id: str) -> List[SwapRequest]:
        """사용자의 교환 요청 조회"""
        if is_demo_mode():
            swaps = get_demo_data("swap_requests")
            return [
                SwapRequest.from_dict(s) for s in swaps
                if s.get("branch_id") == branch_id and
                (s.get("requester") == user_id or s.get("target") == user_id)
            ]

        db = get_db()
        if db is None:
            return []

        try:
            result = db.table("swap_requests").select("*").eq(
                "branch_id", branch_id
            ).or_(f"requester.eq.{user_id},target.eq.{user_id}").order(
                "created_at", desc=True
            ).execute()

            return [SwapRequest.from_dict(s) for s in result.data] if result.data else []
        except Exception:
            return []

    @staticmethod
    def create_swap_request(branch_id: str, requester: str, target: str,
                           swap_date: str, requester_shift: str,
                           target_shift: str, reason: str = "") -> Optional[SwapRequest]:
        """교환 요청 생성"""
        data = {
            "branch_id": branch_id,
            "requester": requester,
            "target": target,
            "swap_date": swap_date,
            "requester_shift": requester_shift,
            "target_shift": target_shift,
            "reason": reason,
            "status": "pending",
        }

        if is_demo_mode():
            data["id"] = str(uuid.uuid4())
            add_demo_data("swap_requests", data)
            return SwapRequest.from_dict(data)

        result = db_insert("swap_requests", data)
        if result:
            return SwapRequest.from_dict(result)
        return None

    @staticmethod
    def approve_swap_request(request_id: str, approved_by: str) -> bool:
        """교환 요청 승인"""
        if is_demo_mode():
            swaps = get_demo_data("swap_requests")
            for s in swaps:
                if s.get("id") == request_id:
                    s["status"] = "approved"
                    s["approved_by"] = approved_by
                    s["approved_at"] = datetime.now().isoformat()
                    set_demo_data("swap_requests", swaps)
                    return True
            return False

        return db_update("swap_requests", {"id": request_id}, {
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": datetime.now().isoformat(),
        }) is not None

    @staticmethod
    def reject_swap_request(request_id: str, rejected_by: str) -> bool:
        """교환 요청 거절"""
        if is_demo_mode():
            swaps = get_demo_data("swap_requests")
            for s in swaps:
                if s.get("id") == request_id:
                    s["status"] = "rejected"
                    s["approved_by"] = rejected_by
                    s["approved_at"] = datetime.now().isoformat()
                    set_demo_data("swap_requests", swaps)
                    return True
            return False

        return db_update("swap_requests", {"id": request_id}, {
            "status": "rejected",
            "approved_by": rejected_by,
            "approved_at": datetime.now().isoformat(),
        }) is not None

    # === 알림 ===

    @staticmethod
    def get_notifications(branch_id: str, user_id: str, unread_only: bool = False) -> List[Notification]:
        """알림 조회"""
        if is_demo_mode():
            notifs = get_demo_data("notifications")
            result = [
                Notification.from_dict(n) for n in notifs
                if n.get("branch_id") == branch_id and n.get("user_id") == user_id
            ]
            if unread_only:
                result = [n for n in result if not n.read]
            return result

        db = get_db()
        if db is None:
            return []

        try:
            query = db.table("notifications").select("*").eq(
                "branch_id", branch_id
            ).eq("user_id", user_id)

            if unread_only:
                query = query.eq("read", False)

            result = query.order("created_at", desc=True).limit(50).execute()
            return [Notification.from_dict(n) for n in result.data] if result.data else []
        except Exception:
            return []

    @staticmethod
    def create_notification(branch_id: str, user_id: str, title: str,
                           message: str, notif_type: str = "info") -> Optional[Notification]:
        """알림 생성"""
        data = {
            "branch_id": branch_id,
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notif_type,
            "read": False,
        }

        if is_demo_mode():
            data["id"] = str(uuid.uuid4())
            add_demo_data("notifications", data)
            return Notification.from_dict(data)

        result = db_insert("notifications", data)
        if result:
            return Notification.from_dict(result)
        return None

    @staticmethod
    def mark_notification_read(notification_id: str) -> bool:
        """알림 읽음 처리"""
        if is_demo_mode():
            notifs = get_demo_data("notifications")
            for n in notifs:
                if n.get("id") == notification_id:
                    n["read"] = True
                    set_demo_data("notifications", notifs)
                    return True
            return False

        return db_update("notifications", {"id": notification_id}, {"read": True}) is not None

    @staticmethod
    def mark_all_read(branch_id: str, user_id: str) -> bool:
        """모든 알림 읽음 처리"""
        if is_demo_mode():
            notifs = get_demo_data("notifications")
            for n in notifs:
                if n.get("branch_id") == branch_id and n.get("user_id") == user_id:
                    n["read"] = True
            set_demo_data("notifications", notifs)
            return True

        db = get_db()
        if db is None:
            return False

        try:
            db.table("notifications").update({"read": True}).eq(
                "branch_id", branch_id
            ).eq("user_id", user_id).execute()
            return True
        except Exception:
            return False

    @staticmethod
    def get_unread_count(branch_id: str, user_id: str) -> int:
        """읽지 않은 알림 수"""
        notifs = ShiftService.get_notifications(branch_id, user_id, unread_only=True)
        return len(notifs)
