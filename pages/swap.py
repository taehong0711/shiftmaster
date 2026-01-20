# pages/swap.py
"""시프트 교환 페이지"""

import streamlit as st
from datetime import date, timedelta
from localization import t
from core.session import get_current_branch_id
from core.auth import get_current_user, is_editor
from models.staff import get_staff_for_branch
from services.shift_service import ShiftService


def render():
    """시프트 교환 페이지 렌더링"""
    st.title(t("swap.title"))

    branch_id = get_current_branch_id()
    if not branch_id:
        st.warning(t("branches.no_branches"))
        return

    user = get_current_user()
    can_approve = is_editor()

    # 탭 구성
    tabs = st.tabs([
        t("swap.new_request"),
        t("swap.my_requests"),
        t("swap.pending_approvals") if can_approve else ""
    ])

    with tabs[0]:
        render_new_request(branch_id, user)

    with tabs[1]:
        render_my_requests(branch_id, user)

    if can_approve and len(tabs) > 2:
        with tabs[2]:
            render_pending_approvals(branch_id, user)


def render_new_request(branch_id: str, user: str):
    """새 교환 요청"""
    st.subheader(t("swap.new_request"))

    staff_list = get_staff_for_branch(branch_id)
    staff_names = [s.name for s in staff_list]

    if not staff_names:
        st.info(t("common.none"))
        return

    with st.form("swap_request_form"):
        col1, col2 = st.columns(2)

        with col1:
            requester = st.selectbox(
                t("swap.requester"),
                options=staff_names,
                index=0
            )
            swap_date = st.date_input(
                t("swap.date"),
                value=date.today() + timedelta(days=1),
                min_value=date.today()
            )
            requester_shift = st.text_input(
                t("swap.requester_shift"),
                placeholder="E1"
            )

        with col2:
            target_options = [n for n in staff_names if n != requester]
            target = st.selectbox(
                t("swap.target"),
                options=target_options if target_options else staff_names
            )
            target_shift = st.text_input(
                t("swap.target_shift"),
                placeholder="G1"
            )

        reason = st.text_area(t("swap.reason"), placeholder="Optional...")

        submitted = st.form_submit_button(t("swap.submit_request"))

        if submitted:
            if not requester_shift or not target_shift:
                st.error(t("errors.validation"))
                return

            result = ShiftService.create_swap_request(
                branch_id=branch_id,
                requester=requester,
                target=target,
                swap_date=str(swap_date),
                requester_shift=requester_shift,
                target_shift=target_shift,
                reason=reason
            )

            if result:
                # 알림 생성
                ShiftService.create_notification(
                    branch_id=branch_id,
                    user_id=target,
                    title=t("swap.title"),
                    message=f"{requester} → {target} ({swap_date})",
                    notif_type="swap"
                )
                st.success(t("swap.request_submitted"))
            else:
                st.error(t("errors.save_failed"))


def render_my_requests(branch_id: str, user: str):
    """내 요청 목록"""
    st.subheader(t("swap.my_requests"))

    # 모든 스태프 이름으로 검색 (실제로는 현재 사용자와 연결된 스태프)
    staff_list = get_staff_for_branch(branch_id)

    all_requests = []
    for staff in staff_list:
        requests = ShiftService.get_user_swap_requests(branch_id, staff.name)
        all_requests.extend(requests)

    # 중복 제거
    seen = set()
    unique_requests = []
    for req in all_requests:
        if req.id not in seen:
            seen.add(req.id)
            unique_requests.append(req)

    if not unique_requests:
        st.info(t("common.none"))
        return

    for req in unique_requests:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

            with col1:
                st.markdown(f"**{req.requester}** → **{req.target}**")
                st.caption(f"{req.swap_date}")

            with col2:
                st.write(f"{req.requester_shift} ↔ {req.target_shift}")
                if req.reason:
                    st.caption(req.reason)

            with col3:
                status_emoji = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌"
                }.get(req.status, "")
                status_text = {
                    "pending": t("swap.pending"),
                    "approved": t("swap.approved"),
                    "rejected": t("swap.rejected")
                }.get(req.status, req.status)
                st.write(f"{status_emoji} {status_text}")

            st.divider()


def render_pending_approvals(branch_id: str, user: str):
    """승인 대기 목록"""
    st.subheader(t("swap.pending_approvals"))

    pending = ShiftService.get_pending_swap_requests(branch_id)

    if not pending:
        st.info(t("common.none"))
        return

    for req in pending:
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                st.markdown(f"**{req.requester}** → **{req.target}**")
                st.caption(f"{req.swap_date}: {req.requester_shift} ↔ {req.target_shift}")
                if req.reason:
                    st.caption(f"Reason: {req.reason}")

            with col2:
                if st.button(t("swap.approve"), key=f"approve_{req.id}",
                           use_container_width=True, type="primary"):
                    if ShiftService.approve_swap_request(req.id, user):
                        # 알림 생성
                        ShiftService.create_notification(
                            branch_id=branch_id,
                            user_id=req.requester,
                            title=t("swap.request_approved"),
                            message=f"{req.swap_date}: {req.requester_shift} ↔ {req.target_shift}",
                            notif_type="success"
                        )
                        st.success(t("swap.request_approved"))
                        st.rerun()

            with col3:
                if st.button(t("swap.reject"), key=f"reject_{req.id}",
                           use_container_width=True):
                    if ShiftService.reject_swap_request(req.id, user):
                        ShiftService.create_notification(
                            branch_id=branch_id,
                            user_id=req.requester,
                            title=t("swap.request_rejected"),
                            message=f"{req.swap_date}: {req.requester_shift} ↔ {req.target_shift}",
                            notif_type="warning"
                        )
                        st.success(t("swap.request_rejected"))
                        st.rerun()

            st.divider()
