# core/auth.py
"""인증 모듈"""

import streamlit as st
from typing import Optional, Tuple
from collections.abc import Mapping
from config.constants import ROLE_SUPER, ROLE_EDITOR, ROLE_VIEWER


def get_app_users() -> dict:
    """secrets.toml에서 앱 유저 정보 가져오기"""
    try:
        if "app_users" not in st.secrets:
            return {}

        users = st.secrets["app_users"]
        if isinstance(users, Mapping):
            # Normalize nested mapping types from st.secrets
            return {
                k: dict(v) if isinstance(v, Mapping) else v
                for k, v in users.items()
            }
        return {}
    except Exception as e:
        st.error(f"secrets 로드 오류: {e}")
        return {}


def authenticate(username: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    사용자 인증

    Args:
        username: 사용자명
        password: 비밀번호

    Returns:
        (인증 성공 여부, 역할)
    """
    users = get_app_users()

    if username in users:
        user_info = users[username]
        if isinstance(user_info, Mapping):
            if user_info.get("password") == password:
                return True, user_info.get("role", ROLE_VIEWER)
        elif isinstance(user_info, str):
            # 단순 비밀번호 형식
            if user_info == password:
                return True, ROLE_VIEWER

    return False, None


def login(username: str, role: str):
    """로그인 상태 설정"""
    st.session_state.auth_ok = True
    st.session_state.auth_user = username
    st.session_state.auth_role = role


def logout():
    """로그아웃"""
    st.session_state.auth_ok = False
    st.session_state.auth_user = None
    st.session_state.auth_role = None
    # 지점 정보도 초기화
    if "current_branch_id" in st.session_state:
        del st.session_state.current_branch_id


def is_authenticated() -> bool:
    """인증 여부 확인"""
    return st.session_state.get("auth_ok", False)


def get_current_user() -> Optional[str]:
    """현재 사용자명 반환"""
    return st.session_state.get("auth_user")


def get_current_role() -> Optional[str]:
    """현재 역할 반환"""
    return st.session_state.get("auth_role")


def is_super() -> bool:
    """super 권한 여부"""
    return get_current_role() == ROLE_SUPER


def is_editor() -> bool:
    """editor 이상 권한 여부"""
    return get_current_role() in [ROLE_SUPER, ROLE_EDITOR]


def is_viewer() -> bool:
    """viewer 이상 권한 (모든 인증 사용자)"""
    return is_authenticated()


def require_login(func):
    """로그인 필요 데코레이터"""
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("ログインが必要です。")
            return
        return func(*args, **kwargs)
    return wrapper


def require_editor(func):
    """editor 권한 필요 데코레이터"""
    def wrapper(*args, **kwargs):
        if not is_editor():
            st.warning("編集者以上の権限が必要です。")
            return
        return func(*args, **kwargs)
    return wrapper


def require_super(func):
    """super 권한 필요 데코레이터"""
    def wrapper(*args, **kwargs):
        if not is_super():
            st.warning("管理者権限が必要です。")
            return
        return func(*args, **kwargs)
    return wrapper


def login_ui():
    """로그인 UI 표시"""
    from localization.i18n import t

    st.title(t("auth.login_title"))

    # 디버깅: 사용 가능한 유저 표시
    users = get_app_users()
    if users:
        st.info(f"등록된 유저: {list(users.keys())}")
    else:
        st.warning("등록된 유저가 없습니다. secrets.toml을 확인하세요.")

    with st.form("login_form"):
        username = st.text_input(t("auth.username")).strip()
        password = st.text_input(t("auth.password"), type="password").strip()
        submit = st.form_submit_button(t("auth.login_button"))

        if submit:
            if not username or not password:
                st.error(t("auth.empty_fields"))
                return False

            success, role = authenticate(username, password)

            if success:
                login(username, role)
                st.success(t("auth.login_success"))
                st.rerun()
            else:
                st.error(t("auth.login_failed"))

    return False
