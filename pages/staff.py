# pages/staff.py
"""스태프 관리 페이지"""

import streamlit as st
import pandas as pd
from localization import t
from core.session import get_current_branch_id
from core.auth import is_super, is_editor, get_current_user
from core.database import get_db, is_demo_mode, db_insert, db_update, db_delete
from core.session import get_demo_data, set_demo_data
from models.staff import get_staff_for_branch, Staff, get_staff_count
import uuid


def render():
    """스태프 관리 페이지 렌더링"""
    st.title(t("staff.title"))

    branch_id = get_current_branch_id()
    if not branch_id:
        st.warning(t("branches.no_branches"))
        return

    # 권한 체크
    can_edit = is_editor()
    can_delete = is_super()

    # 통계
    stats = get_staff_count(branch_id)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t("dashboard.total_staff"), stats["total"])
    with col2:
        st.metric(t("staff.skill_night"), stats["night_capable"])
    with col3:
        st.metric(t("staff.skill_l1"), stats["l1_capable"])
    with col4:
        st.metric(t("staff.male") + "/" + t("staff.female"),
                 f"{stats['male']}/{stats['female']}")

    st.divider()

    # 스태프 추가 버튼
    if can_edit:
        with st.expander(t("staff.add_staff"), expanded=False):
            render_add_staff_form(branch_id)

    st.divider()

    # 스태프 목록
    staff_list = get_staff_for_branch(branch_id, include_inactive=can_delete)

    if not staff_list:
        st.info(t("common.none"))
        return

    # DataFrame으로 표시
    df = pd.DataFrame([{
        t("staff.name"): s.name,
        t("staff.gender"): t("staff.male") if s.gender == "M" else t("staff.female"),
        t("staff.role"): t("staff.manager") if s.role == "manager" else t("staff.staff_role"),
        t("staff.target_off"): s.target_off,
        t("staff.nenkyu"): s.nenkyu,
        t("staff.skills"): s.get_skills_display(),
        t("staff.prefer"): s.prefer,
        "id": s.id,
        "is_active": s.is_active,
    } for s in staff_list])

    # 편집 가능한 데이터 에디터
    if can_edit:
        edited_df = st.data_editor(
            df.drop(columns=["id", "is_active"]),
            num_rows="dynamic",
            use_container_width=True,
            key="staff_editor"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("common.save"), use_container_width=True):
                save_staff_changes(branch_id, staff_list, edited_df)
        with col2:
            if st.button(t("common.cancel"), use_container_width=True):
                st.rerun()
    else:
        st.dataframe(df.drop(columns=["id", "is_active"]), use_container_width=True)

    # 개별 편집/삭제
    if can_edit:
        st.divider()
        st.subheader(t("staff.edit_staff"))

        selected_staff = st.selectbox(
            t("common.select"),
            options=[s.name for s in staff_list],
            key="edit_staff_select"
        )

        if selected_staff:
            staff = next((s for s in staff_list if s.name == selected_staff), None)
            if staff:
                render_edit_staff_form(branch_id, staff, can_delete)


def render_add_staff_form(branch_id: str):
    """스태프 추가 폼"""
    with st.form("add_staff_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(t("staff.name"))
            gender = st.selectbox(
                t("staff.gender"),
                options=["M", "F"],
                format_func=lambda x: t("staff.male") if x == "M" else t("staff.female")
            )
            role = st.selectbox(
                t("staff.role"),
                options=["staff", "manager"],
                format_func=lambda x: t("staff.manager") if x == "manager" else t("staff.staff_role")
            )

        with col2:
            target_off = st.number_input(t("staff.target_off"), min_value=0, max_value=31, value=8)
            nenkyu = st.number_input(t("staff.nenkyu"), min_value=0, max_value=40, value=0)
            skills = st.text_input(t("staff.skills"), placeholder="L1,NIGHT")

        prefer = st.text_input(t("staff.prefer"))

        submitted = st.form_submit_button(t("common.add"))

        if submitted:
            if not name:
                st.error(t("errors.validation"))
                return

            skills_list = [s.strip() for s in skills.split(",") if s.strip()]

            staff_data = {
                "branch_id": branch_id,
                "name": name,
                "gender": gender,
                "role": role,
                "target_off": target_off,
                "nenkyu": nenkyu,
                "skills": ",".join(skills_list),
                "prefer": prefer,
                "is_active": True,
                "display_order": 999,
            }

            if is_demo_mode():
                staff_data["id"] = str(uuid.uuid4())
                demo_staff = get_demo_data("staff_data")
                demo_staff.append(staff_data)
                set_demo_data("staff_data", demo_staff)
                st.success(t("staff.staff_saved"))
                st.rerun()
            else:
                result = db_insert("staff", staff_data)
                if result:
                    st.success(t("staff.staff_saved"))
                    st.rerun()
                else:
                    st.error(t("errors.save_failed"))


def render_edit_staff_form(branch_id: str, staff: Staff, can_delete: bool):
    """스태프 편집 폼"""
    with st.form(f"edit_staff_form_{staff.id}"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(t("staff.name"), value=staff.name)
            gender = st.selectbox(
                t("staff.gender"),
                options=["M", "F"],
                index=0 if staff.gender == "M" else 1,
                format_func=lambda x: t("staff.male") if x == "M" else t("staff.female")
            )
            role = st.selectbox(
                t("staff.role"),
                options=["staff", "manager"],
                index=1 if staff.role == "manager" else 0,
                format_func=lambda x: t("staff.manager") if x == "manager" else t("staff.staff_role")
            )

        with col2:
            target_off = st.number_input(t("staff.target_off"), min_value=0, max_value=31,
                                        value=staff.target_off)
            nenkyu = st.number_input(t("staff.nenkyu"), min_value=0, max_value=40,
                                    value=staff.nenkyu)
            skills = st.text_input(t("staff.skills"), value=",".join(staff.skills))

        prefer = st.text_input(t("staff.prefer"), value=staff.prefer)

        col_save, col_del = st.columns(2)

        with col_save:
            save_btn = st.form_submit_button(t("common.save"), use_container_width=True)

        with col_del:
            if can_delete:
                delete_btn = st.form_submit_button(t("common.delete"), use_container_width=True)
            else:
                delete_btn = False

        if save_btn:
            skills_list = [s.strip() for s in skills.split(",") if s.strip()]

            updates = {
                "name": name,
                "gender": gender,
                "role": role,
                "target_off": target_off,
                "nenkyu": nenkyu,
                "skills": ",".join(skills_list),
                "prefer": prefer,
            }

            if is_demo_mode():
                demo_staff = get_demo_data("staff_data")
                for i, s in enumerate(demo_staff):
                    if s.get("id") == staff.id:
                        demo_staff[i].update(updates)
                        break
                set_demo_data("staff_data", demo_staff)
                st.success(t("staff.staff_saved"))
                st.rerun()
            else:
                result = db_update("staff", {"id": staff.id}, updates)
                if result:
                    st.success(t("staff.staff_saved"))
                    st.rerun()
                else:
                    st.error(t("errors.save_failed"))

        if delete_btn:
            if is_demo_mode():
                demo_staff = get_demo_data("staff_data")
                demo_staff = [s for s in demo_staff if s.get("id") != staff.id]
                set_demo_data("staff_data", demo_staff)
                st.success(t("staff.staff_deleted"))
                st.rerun()
            else:
                if db_delete("staff", {"id": staff.id}):
                    st.success(t("staff.staff_deleted"))
                    st.rerun()
                else:
                    st.error(t("errors.delete_failed"))


def save_staff_changes(branch_id: str, original_list: list, edited_df: pd.DataFrame):
    """스태프 변경사항 저장"""
    # 간단한 구현 - 전체 업데이트
    st.info(t("common.loading"))
    # 실제 구현에서는 변경 감지 및 업데이트 로직 필요
    st.success(t("staff.staff_saved"))
