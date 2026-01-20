# pages/dashboard.py
"""대시보드 페이지"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from localization import t
from core.session import get_current_branch_id
from models.staff import get_staff_for_branch, get_staff_count
from services.shift_service import ShiftService


def render():
    """대시보드 렌더링"""
    st.title(t("dashboard.title"))

    branch_id = get_current_branch_id()
    if not branch_id:
        st.warning(t("branches.no_branches"))
        return

    # 스태프 통계
    staff_list = get_staff_for_branch(branch_id)
    stats = get_staff_count(branch_id)

    # 메트릭 카드
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(t("dashboard.total_staff"), stats["total"])

    with col2:
        st.metric(t("dashboard.managers"), stats["managers"])

    with col3:
        st.metric(t("dashboard.staff_members"), stats["staff"])

    with col4:
        avg_off = sum(s.target_off for s in staff_list) / len(staff_list) if staff_list else 0
        st.metric(t("dashboard.avg_off_days"), f"{avg_off:.1f}")

    st.divider()

    # 차트 영역
    col_left, col_right = st.columns(2)

    with col_left:
        # 역할 분포 파이 차트
        st.subheader(t("dashboard.role_distribution"))
        if staff_list:
            role_data = {
                t("staff.manager"): stats["managers"],
                t("staff.staff_role"): stats["staff"]
            }
            fig_role = px.pie(
                values=list(role_data.values()),
                names=list(role_data.keys()),
                hole=0.4
            )
            fig_role.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig_role, use_container_width=True)
        else:
            st.info(t("common.none"))

    with col_right:
        # 성별 분포 파이 차트
        st.subheader(t("dashboard.gender_distribution"))
        if staff_list:
            gender_data = {
                t("staff.male"): stats["male"],
                t("staff.female"): stats["female"]
            }
            fig_gender = px.pie(
                values=list(gender_data.values()),
                names=list(gender_data.keys()),
                hole=0.4,
                color_discrete_sequence=["#4A90D9", "#E91E63"]
            )
            fig_gender.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig_gender, use_container_width=True)
        else:
            st.info(t("common.none"))

    st.divider()

    # 스킬 커버리지
    st.subheader(t("dashboard.skill_coverage"))
    if staff_list:
        skill_data = {
            t("staff.skill_l1"): stats["l1_capable"],
            t("staff.skill_night"): stats["night_capable"]
        }
        fig_skill = go.Figure(go.Bar(
            x=list(skill_data.values()),
            y=list(skill_data.keys()),
            orientation='h',
            marker_color=['#9C27B0', '#F44336']
        ))
        fig_skill.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=150,
            xaxis_title=t("dashboard.total_staff")
        )
        st.plotly_chart(fig_skill, use_container_width=True)

    # 휴일 수 분포
    st.subheader(t("dashboard.off_days_distribution"))
    if staff_list:
        off_days = [s.target_off for s in staff_list]
        fig_off = px.histogram(
            x=off_days,
            nbins=10,
            labels={'x': t("staff.target_off"), 'y': t("dashboard.total_staff")}
        )
        fig_off.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=200
        )
        st.plotly_chart(fig_off, use_container_width=True)

    st.divider()

    # 빠른 작업
    st.subheader(t("dashboard.quick_actions"))
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button(t("dashboard.go_to_schedule"), use_container_width=True):
            st.session_state.current_page = "schedule"
            st.rerun()

    with col_btn2:
        if st.button(t("dashboard.go_to_staff"), use_container_width=True):
            st.session_state.current_page = "staff"
            st.rerun()

    with col_btn3:
        if st.button(t("nav.constraints"), use_container_width=True):
            st.session_state.current_page = "constraints"
            st.rerun()

    # 최근 알림
    st.divider()
    st.subheader(t("dashboard.recent_notifications"))

    from core.auth import get_current_user
    user = get_current_user()
    if user:
        notifications = ShiftService.get_notifications(branch_id, user)[:5]
        if notifications:
            for notif in notifications:
                icon = "🔔" if not notif.read else "✓"
                st.markdown(f"{icon} **{notif.title}** - {notif.message}")
        else:
            st.info(t("notifications.no_notifications"))
    else:
        st.info(t("notifications.no_notifications"))
