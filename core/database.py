# core/database.py
"""Supabase 데이터베이스 클라이언트 모듈"""

import streamlit as st
from typing import Optional
from supabase import create_client, Client


class SupabaseClient:
    """Supabase 클라이언트 싱글톤"""

    _instance: Optional[Client] = None
    _demo_mode: bool = False

    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Supabase 클라이언트를 반환. 데모 모드면 None 반환."""
        if cls._instance is None:
            cls._init_client()
        return cls._instance

    @classmethod
    def is_demo_mode(cls) -> bool:
        """데모 모드 여부 반환"""
        if cls._instance is None:
            cls._init_client()
        return cls._demo_mode

    @classmethod
    def _init_client(cls):
        """Supabase 클라이언트 초기화"""
        try:
            url = st.secrets.get("SUPABASE_URL", "")
            key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")

            # 플레이스홀더 값 또는 빈 값 체크
            if not url or not key:
                cls._demo_mode = True
                cls._instance = None
                return

            if "your-project" in url or "your-service-role-key" in key:
                cls._demo_mode = True
                cls._instance = None
                return

            cls._instance = create_client(url, key)
            cls._demo_mode = False

        except Exception as e:
            st.warning(f"Supabase 연결 실패: {e}")
            cls._demo_mode = True
            cls._instance = None

    @classmethod
    def reset(cls):
        """클라이언트 리셋 (테스트용)"""
        cls._instance = None
        cls._demo_mode = False


def get_db() -> Optional[Client]:
    """Supabase 클라이언트 가져오기"""
    return SupabaseClient.get_client()


def is_demo_mode() -> bool:
    """데모 모드 여부 확인"""
    return SupabaseClient.is_demo_mode()


# === 범용 DB 헬퍼 함수 ===

def db_select(table: str, columns: str = "*", filters: dict = None, order_by: str = None, limit: int = None):
    """
    테이블에서 데이터 조회

    Args:
        table: 테이블 이름
        columns: 조회할 컬럼 (기본: *)
        filters: 필터 조건 딕셔너리 (예: {"user_id": "abc", "is_active": True})
        order_by: 정렬 기준 (예: "created_at.desc")
        limit: 조회 개수 제한

    Returns:
        조회 결과 리스트 또는 빈 리스트
    """
    client = get_db()
    if client is None:
        return []

    try:
        query = client.table(table).select(columns)

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        if order_by:
            parts = order_by.split(".")
            col = parts[0]
            desc = len(parts) > 1 and parts[1] == "desc"
            query = query.order(col, desc=desc)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []

    except Exception as e:
        st.error(f"DB 조회 오류 ({table}): {e}")
        return []


def db_insert(table: str, data: dict):
    """
    테이블에 데이터 삽입

    Args:
        table: 테이블 이름
        data: 삽입할 데이터 딕셔너리

    Returns:
        삽입된 데이터 또는 None
    """
    client = get_db()
    if client is None:
        return None

    try:
        result = client.table(table).insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"DB 삽입 오류 ({table}): {e}")
        return None


def db_update(table: str, filters: dict, data: dict):
    """
    테이블 데이터 업데이트

    Args:
        table: 테이블 이름
        filters: 대상 조건 딕셔너리
        data: 업데이트할 데이터 딕셔너리

    Returns:
        업데이트된 데이터 또는 None
    """
    client = get_db()
    if client is None:
        return None

    try:
        query = client.table(table).update(data)

        for key, value in filters.items():
            query = query.eq(key, value)

        result = query.execute()
        return result.data if result.data else None
    except Exception as e:
        st.error(f"DB 업데이트 오류 ({table}): {e}")
        return None


def db_upsert(table: str, data: dict, on_conflict: str = None):
    """
    테이블에 데이터 upsert (존재하면 업데이트, 없으면 삽입)

    Args:
        table: 테이블 이름
        data: 삽입/업데이트할 데이터 딕셔너리
        on_conflict: 충돌 체크 컬럼 (예: "id" 또는 "user_id,branch_id")

    Returns:
        결과 데이터 또는 None
    """
    client = get_db()
    if client is None:
        return None

    try:
        if on_conflict:
            result = client.table(table).upsert(data, on_conflict=on_conflict).execute()
        else:
            result = client.table(table).upsert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"DB upsert 오류 ({table}): {e}")
        return None


def db_delete(table: str, filters: dict):
    """
    테이블에서 데이터 삭제

    Args:
        table: 테이블 이름
        filters: 삭제 대상 조건 딕셔너리

    Returns:
        삭제 성공 여부
    """
    client = get_db()
    if client is None:
        return False

    try:
        query = client.table(table).delete()

        for key, value in filters.items():
            query = query.eq(key, value)

        query.execute()
        return True
    except Exception as e:
        st.error(f"DB 삭제 오류 ({table}): {e}")
        return False
