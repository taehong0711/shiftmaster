# core/session.py
"""세션 관리 모듈"""

import streamlit as st
from typing import Any, Optional
from config.constants import DEFAULT_LANGUAGE, DEFAULT_DAY_SHIFTS, DEFAULT_NIGHT_SHIFTS


def init_session():
    """세션 상태 초기화"""
    defaults = {
        # 인증
        "auth_ok": False,
        "auth_user": None,
        "auth_role": None,

        # 지점
        "current_branch_id": None,
        "current_branch_name": None,

        # 언어
        "language": DEFAULT_LANGUAGE,

        # 테마
        "theme_mode": "light",

        # 페이지
        "current_page": "dashboard",

        # 시프트 설정
        "shifts_day": DEFAULT_DAY_SHIFTS.copy(),
        "shifts_night": DEFAULT_NIGHT_SHIFTS.copy(),

        # 데모 모드 데이터
        "demo_staff_data": [],
        "demo_monthly_shifts": {},
        "demo_branches": [],
        "demo_constraints": [],
        "demo_notifications": [],
        "demo_swap_requests": [],

        # 솔버 상태
        "stage1_results": None,
        "stage2_results": None,
        "selected_stage1_idx": 0,
        "selected_stage2_idx": 0,

        # 편집 상태
        "edited_cells": {},

        # 캐시 버전 (캐시 무효화용)
        "cache_version": 1,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_session(key: str, default: Any = None) -> Any:
    """세션 값 가져오기"""
    return st.session_state.get(key, default)


def set_session(key: str, value: Any):
    """세션 값 설정"""
    st.session_state[key] = value


def update_session(**kwargs):
    """여러 세션 값 업데이트"""
    for key, value in kwargs.items():
        st.session_state[key] = value


def clear_session_key(key: str):
    """특정 세션 키 삭제"""
    if key in st.session_state:
        del st.session_state[key]


def clear_solver_state():
    """솔버 관련 상태 초기화"""
    st.session_state.stage1_results = None
    st.session_state.stage2_results = None
    st.session_state.selected_stage1_idx = 0
    st.session_state.selected_stage2_idx = 0
    st.session_state.edited_cells = {}


def increment_cache_version():
    """캐시 버전 증가 (캐시 무효화)"""
    st.session_state.cache_version = st.session_state.get("cache_version", 1) + 1


def get_versioned_key(base_key: str) -> str:
    """버전화된 키 생성 (캐시용)"""
    version = st.session_state.get("cache_version", 1)
    return f"{base_key}_v{version}"


# === 지점 관련 ===

def get_current_branch_id() -> Optional[str]:
    """현재 선택된 지점 ID"""
    return st.session_state.get("current_branch_id")


def set_current_branch(branch_id: str, branch_name: str = None):
    """현재 지점 설정"""
    st.session_state.current_branch_id = branch_id
    if branch_name:
        st.session_state.current_branch_name = branch_name
    # 지점 변경 시 솔버 상태 초기화
    clear_solver_state()

    # 지점별 시프트 코드 로드 (lazy import로 순환 참조 방지)
    from services.branch_service import BranchService
    shift_codes = BranchService.get_branch_shift_codes(branch_id)
    st.session_state.shifts_day = shift_codes.get("day_shifts", DEFAULT_DAY_SHIFTS.copy())
    st.session_state.shifts_night = shift_codes.get("night_shifts", DEFAULT_NIGHT_SHIFTS.copy())


def get_current_branch_name() -> Optional[str]:
    """현재 선택된 지점 이름"""
    return st.session_state.get("current_branch_name")


# === 언어 관련 ===

def get_language() -> str:
    """현재 언어 코드 반환"""
    return st.session_state.get("language", DEFAULT_LANGUAGE)


def set_language(lang_code: str):
    """언어 설정"""
    st.session_state.language = lang_code


# === 테마 관련 ===

def get_theme() -> str:
    """현재 테마 반환"""
    return st.session_state.get("theme_mode", "light")


def set_theme(theme: str):
    """테마 설정"""
    st.session_state.theme_mode = theme


def toggle_theme():
    """테마 토글"""
    current = get_theme()
    set_theme("dark" if current == "light" else "light")


# === 페이지 관련 ===

def get_current_page() -> str:
    """현재 페이지 반환"""
    return st.session_state.get("current_page", "dashboard")


def set_current_page(page: str):
    """페이지 설정"""
    st.session_state.current_page = page


# === 데모 모드 데이터 관리 ===

def get_demo_data(key: str) -> list:
    """데모 모드 데이터 가져오기"""
    return st.session_state.get(f"demo_{key}", [])


def set_demo_data(key: str, data: list):
    """데모 모드 데이터 설정"""
    st.session_state[f"demo_{key}"] = data


def add_demo_data(key: str, item: dict):
    """데모 모드 데이터에 항목 추가"""
    data = get_demo_data(key)
    data.append(item)
    set_demo_data(key, data)


def update_demo_data(key: str, filter_key: str, filter_value: Any, updates: dict):
    """데모 모드 데이터 업데이트"""
    data = get_demo_data(key)
    for item in data:
        if item.get(filter_key) == filter_value:
            item.update(updates)
            break
    set_demo_data(key, data)


def delete_demo_data(key: str, filter_key: str, filter_value: Any):
    """데모 모드 데이터 삭제"""
    data = get_demo_data(key)
    data = [item for item in data if item.get(filter_key) != filter_value]
    set_demo_data(key, data)
