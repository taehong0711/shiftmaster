# app.py
"""Hotel Shift Pro v2.0 - 메인 진입점"""

import streamlit as st
import os

# 페이지 설정 (반드시 첫 번째 Streamlit 명령어)
st.set_page_config(
    page_title="Hotel Shift Pro",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 모듈 임포트
from config.constants import APP_NAME, APP_VERSION, PAGES, SUPPORTED_LANGUAGES
from core.session import init_session, get_current_page, set_current_page, get_current_branch_id, set_current_branch
from core.auth import is_authenticated, login_ui, logout, get_current_user, get_current_role
from core.database import is_demo_mode
from services.branch_service import BranchService
from services.constraint_service import ConstraintService
from services.shift_service import ShiftService
from localization import t, set_language, get_current_language
from components.mobile_nav import inject_mobile_css, render_mobile_nav

# 페이지 모듈 임포트
from pages import dashboard, schedule, staff, constraints, branches, settings, swap, requests_page


def main():
    """메인 함수"""
    # 세션 초기화
    init_session()

    # CSS 주입
    inject_mobile_css()
    load_custom_css()

    # 데모 모드 경고
    if is_demo_mode():
        st.warning(f"⚠️ {t('demo.mode_active')}: {t('demo.mode_description')}")

    # 인증 체크
    if not is_authenticated():
        login_ui()
        return

    # 지점 초기화
    init_branch()

    # 사이드바 렌더링
    render_sidebar()

    # 메인 컨텐츠
    render_main_content()

    # 모바일 하단 네비게이션
    render_mobile_nav()


def init_branch():
    """지점 초기화"""
    branch_id = get_current_branch_id()

    if not branch_id:
        # 기본 지점 생성/확인
        default_branch = BranchService.ensure_default_branch()
        if default_branch:
            set_current_branch(default_branch.id, default_branch.name)

            # 기본 제약 초기화
            ConstraintService.init_default_constraints(default_branch.id)


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        # 로고 및 타이틀
        st.markdown(f"# 🏨 {APP_NAME}")
        st.caption(f"{APP_VERSION}")

        st.divider()

        # 지점 선택
        render_branch_selector()

        st.divider()

        # 언어 선택
        render_language_selector()

        st.divider()

        # 네비게이션 메뉴
        render_navigation()

        st.divider()

        # 사용자 정보
        render_user_info()

        st.divider()

        # 알림
        render_notifications_badge()


def render_branch_selector():
    """지점 선택 드롭다운"""
    user = get_current_user()
    branches_list = BranchService.get_user_branches(user) if user else BranchService.get_all_branches()

    if not branches_list:
        st.info(t("branches.no_branches"))
        return

    current_branch_id = get_current_branch_id()

    branch_options = {b.id: b.name for b in branches_list}
    branch_ids = list(branch_options.keys())

    # 현재 지점 인덱스
    current_idx = 0
    if current_branch_id in branch_ids:
        current_idx = branch_ids.index(current_branch_id)

    selected_id = st.selectbox(
        t("branches.select_branch"),
        options=branch_ids,
        index=current_idx,
        format_func=lambda x: branch_options.get(x, x),
        key="sidebar_branch_select"
    )

    if selected_id != current_branch_id:
        selected_branch = next((b for b in branches_list if b.id == selected_id), None)
        if selected_branch:
            set_current_branch(selected_id, selected_branch.name)
            st.rerun()


def render_language_selector():
    """언어 선택"""
    current_lang = get_current_language()

    lang_options = list(SUPPORTED_LANGUAGES.keys())
    current_idx = lang_options.index(current_lang) if current_lang in lang_options else 0

    selected_lang = st.selectbox(
        t("settings.language"),
        options=lang_options,
        index=current_idx,
        format_func=lambda x: SUPPORTED_LANGUAGES.get(x, x),
        key="sidebar_lang_select"
    )

    if selected_lang != current_lang:
        set_language(selected_lang)
        st.rerun()


def render_navigation():
    """네비게이션 메뉴"""
    st.subheader(t("common.select"))

    current_page = get_current_page()
    lang = get_current_language()

    # 페이지 목록
    page_keys = ["dashboard", "schedule", "requests", "staff", "constraints", "branches", "swap", "settings"]

    for page_key in page_keys:
        if page_key in PAGES:
            page_info = PAGES[page_key]
            icon = page_info.get("icon", "📄")
            name = page_info.get(f"name_{lang}", page_info.get("name_ja", page_key))

            is_current = page_key == current_page
            button_type = "primary" if is_current else "secondary"

            if st.button(
                f"{icon} {name}",
                key=f"nav_{page_key}",
                use_container_width=True,
                type=button_type
            ):
                set_current_page(page_key)
                st.rerun()


def render_user_info():
    """사용자 정보"""
    user = get_current_user()
    role = get_current_role()

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption(f"👤 {user}")
        role_badge = {
            "super": "🔴 Super",
            "editor": "🟡 Editor",
            "viewer": "🟢 Viewer"
        }.get(role, role)
        st.caption(role_badge)

    with col2:
        if st.button("🚪", key="logout_btn", help=t("auth.logout_button")):
            logout()
            st.rerun()


def render_notifications_badge():
    """알림 뱃지"""
    branch_id = get_current_branch_id()
    user = get_current_user()

    if branch_id and user:
        unread_count = ShiftService.get_unread_count(branch_id, user)
        if unread_count > 0:
            st.warning(f"🔔 {t('notifications.unread_count', count=unread_count)}")


def render_main_content():
    """메인 컨텐츠 렌더링"""
    current_page = get_current_page()

    # 페이지 라우팅
    page_modules = {
        "dashboard": dashboard,
        "schedule": schedule,
        "requests": requests_page,
        "staff": staff,
        "constraints": constraints,
        "branches": branches,
        "swap": swap,
        "settings": settings,
    }

    if current_page in page_modules:
        page_modules[current_page].render()
    else:
        st.error(t("errors.not_found"))
        dashboard.render()


def load_custom_css():
    """커스텀 CSS 로드"""
    css_path = os.path.join(os.path.dirname(__file__), "static", "css")

    # base.css
    base_css_path = os.path.join(css_path, "base.css")
    if os.path.exists(base_css_path):
        with open(base_css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # responsive.css
    responsive_css_path = os.path.join(css_path, "responsive.css")
    if os.path.exists(responsive_css_path):
        with open(responsive_css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
