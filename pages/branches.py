# pages/branches.py
"""지점 관리 페이지"""

import streamlit as st
from localization import t
from core.session import get_current_branch_id, set_current_branch, set_session
from core.auth import is_super, is_editor, get_current_user
from services.branch_service import BranchService
from config.constants import ROLE_SUPER, ROLE_EDITOR, ROLE_VIEWER, DEFAULT_DAY_SHIFTS, DEFAULT_NIGHT_SHIFTS


def render():
    """지점 관리 페이지 렌더링"""
    st.title(t("branches.title"))

    can_manage = is_super()
    user = get_current_user()

    # 현재 지점 표시
    current_branch_id = get_current_branch_id()
    if current_branch_id:
        current_branch = BranchService.get_branch_by_id(current_branch_id)
        if current_branch:
            st.info(f"{t('branches.current_branch')}: **{current_branch.name}** ({current_branch.code})")

    st.divider()

    # 지점 목록
    branches = BranchService.get_all_branches(active_only=not can_manage)

    if not branches:
        st.warning(t("branches.no_branches"))
        if can_manage:
            if st.button(t("branches.add_branch")):
                default = BranchService.ensure_default_branch()
                if default:
                    st.success(t("branches.branch_created"))
                    set_current_branch(default.id, default.name)
                    st.rerun()
        return

    # 지점 선택
    st.subheader(t("branches.select_branch"))

    cols = st.columns(min(len(branches), 4))
    for i, branch in enumerate(branches):
        col_idx = i % 4
        with cols[col_idx]:
            is_current = branch.id == current_branch_id
            button_type = "primary" if is_current else "secondary"

            if st.button(
                f"{'✓ ' if is_current else ''}{branch.name}",
                key=f"branch_{branch.id}",
                use_container_width=True,
                type=button_type
            ):
                set_current_branch(branch.id, branch.name)
                st.success(f"{branch.name} {t('common.select')}")
                st.rerun()

    st.divider()

    # 지점 관리 (super만)
    if can_manage:
        render_branch_management(branches)


def render_branch_management(branches: list):
    """지점 관리 영역"""
    st.subheader(t("branches.title"))

    # 지점 추가
    with st.expander(t("branches.add_branch"), expanded=False):
        render_add_branch_form()

    st.divider()

    # 지점 목록 및 편집
    for branch in branches:
        with st.expander(f"{branch.name} ({branch.code})", expanded=False):
            render_edit_branch_form(branch)


def render_add_branch_form():
    """지점 추가 폼"""
    with st.form("add_branch_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(t("branches.name"))
            code = st.text_input(t("branches.code"), placeholder="TOKYO_MAIN")

        with col2:
            timezone = st.selectbox(
                t("branches.timezone"),
                options=["Asia/Tokyo", "Asia/Seoul", "UTC", "America/New_York", "Europe/London"],
                index=0
            )

        submitted = st.form_submit_button(t("common.add"))

        if submitted:
            if not name or not code:
                st.error(t("errors.validation"))
                return

            # 코드 중복 체크
            existing = BranchService.get_branch_by_code(code)
            if existing:
                st.error(f"{code} - {t('errors.validation')}")
                return

            result = BranchService.create_branch(name, code, timezone)
            if result:
                st.success(t("branches.branch_created"))
                st.rerun()
            else:
                st.error(t("errors.save_failed"))


def render_edit_branch_form(branch):
    """지점 편집 폼"""
    with st.form(f"edit_branch_{branch.id}"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(t("branches.name"), value=branch.name)
            code = st.text_input(t("branches.code"), value=branch.code, disabled=True)

        with col2:
            timezones = ["Asia/Tokyo", "Asia/Seoul", "UTC", "America/New_York", "Europe/London"]
            tz_idx = timezones.index(branch.timezone) if branch.timezone in timezones else 0
            timezone = st.selectbox(
                t("branches.timezone"),
                options=timezones,
                index=tz_idx,
                key=f"tz_{branch.id}"
            )
            is_active = st.checkbox(t("branches.is_active"), value=branch.is_active)

        col_save, col_del = st.columns(2)

        with col_save:
            save_btn = st.form_submit_button(t("common.save"), use_container_width=True)

        with col_del:
            delete_btn = st.form_submit_button(t("common.delete"), use_container_width=True)

        if save_btn:
            success = BranchService.update_branch(
                branch.id,
                name=name,
                timezone=timezone,
                is_active=is_active
            )
            if success:
                st.success(t("branches.branch_updated"))
                st.rerun()
            else:
                st.error(t("errors.save_failed"))

        if delete_btn:
            # 확인 모달 대신 간단한 비활성화
            success = BranchService.delete_branch(branch.id)
            if success:
                st.success(t("branches.branch_deleted"))
                st.rerun()
            else:
                st.error(t("errors.delete_failed"))

    # 시프트 코드 설정
    st.subheader(t("branches.shift_settings"))
    render_branch_shift_settings(branch)

    st.divider()

    # 사용자 할당
    st.subheader(t("branches.assign_users"))
    render_user_assignment(branch)


def render_user_assignment(branch):
    """사용자 할당"""
    # 간단한 사용자 목록 (실제로는 DB에서 가져와야 함)
    col1, col2, col3 = st.columns(3)

    with col1:
        user_id = st.text_input(t("auth.username"), key=f"assign_user_{branch.id}")

    with col2:
        role = st.selectbox(
            t("branches.user_role"),
            options=[ROLE_SUPER, ROLE_EDITOR, ROLE_VIEWER],
            format_func=lambda x: {
                ROLE_SUPER: t("auth.login_title") + " (Super)",
                ROLE_EDITOR: t("common.edit") + " (Editor)",
                ROLE_VIEWER: t("common.info") + " (Viewer)"
            }.get(x, x),
            key=f"assign_role_{branch.id}"
        )

    with col3:
        st.write("")  # 간격
        st.write("")
        if st.button(t("common.add"), key=f"assign_btn_{branch.id}"):
            if user_id:
                success = BranchService.assign_user_to_branch(user_id, branch.id, role)
                if success:
                    st.success(t("common.success"))
                else:
                    st.error(t("errors.save_failed"))


def render_branch_shift_settings(branch):
    """지점별 시프트 코드 설정"""
    # 현재 지점의 시프트 코드 가져오기
    shift_codes = BranchService.get_branch_shift_codes(branch.id)
    current_day_shifts = shift_codes.get("day_shifts", DEFAULT_DAY_SHIFTS)
    current_night_shifts = shift_codes.get("night_shifts", DEFAULT_NIGHT_SHIFTS)

    st.caption(t("branches.shift_codes_info"))

    col1, col2 = st.columns(2)

    with col1:
        day_shifts_str = st.text_area(
            t("settings.day_shifts"),
            value=", ".join(current_day_shifts),
            key=f"day_shifts_{branch.id}",
            help=t("branches.shift_codes_help")
        )

    with col2:
        night_shifts_str = st.text_area(
            t("settings.night_shifts"),
            value=", ".join(current_night_shifts),
            key=f"night_shifts_{branch.id}",
            help=t("branches.shift_codes_help")
        )

    if st.button(t("common.save"), key=f"save_shifts_{branch.id}"):
        # 문자열을 리스트로 변환 (쉼표로 구분, 공백 제거)
        day_shifts = [s.strip() for s in day_shifts_str.split(",") if s.strip()]
        night_shifts = [s.strip() for s in night_shifts_str.split(",") if s.strip()]

        if day_shifts and night_shifts:
            success = BranchService.update_branch_shift_codes(branch.id, day_shifts, night_shifts)
            if success:
                # 현재 지점이면 세션도 업데이트
                current_branch_id = get_current_branch_id()
                if current_branch_id == branch.id:
                    set_session("shifts_day", day_shifts)
                    set_session("shifts_night", night_shifts)
                st.success(t("branches.branch_updated"))
                st.rerun()
            else:
                st.error(t("errors.save_failed"))
        else:
            st.error(t("errors.validation"))
