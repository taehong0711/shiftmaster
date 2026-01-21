# pages/constraints.py
"""제약 조건 관리 페이지"""

import streamlit as st
from localization import t
from core.session import get_current_branch_id, get_current_branch_name
from core.auth import is_editor, is_super
from services.constraint_service import ConstraintService
from config.constants import CONSTRAINT_CATEGORIES
from config.default_constraints import CONSTRAINT_PRESETS


def render():
    """제약 조건 관리 페이지 렌더링"""
    st.title(t("constraints.title"))

    branch_id = get_current_branch_id()
    if not branch_id:
        st.warning(t("branches.no_branches"))
        return

    # 현재 지점 표시
    branch_name = get_current_branch_name()
    if branch_name:
        st.info(f"{t('constraints.current_branch_notice')}: **{branch_name}**")

    can_edit = is_editor()

    # 요약 정보
    summary = ConstraintService.get_constraints_summary(branch_id)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t("common.all"), summary["total"])
    with col2:
        st.metric(t("common.enabled"), summary["enabled"])
    with col3:
        st.metric(t("constraints.hard_constraints"), summary["hard"])
    with col4:
        st.metric(t("constraints.soft_constraints"), summary["soft"])

    st.divider()

    # 프리셋
    if can_edit:
        render_presets(branch_id)
        st.divider()

    # 제약 목록
    render_constraint_list(branch_id, can_edit)

    # 제약 추가
    if can_edit and is_super():
        st.divider()
        render_add_constraint(branch_id)


def render_presets(branch_id: str):
    """프리셋 영역"""
    st.subheader(t("constraints.presets.title"))

    cols = st.columns(len(CONSTRAINT_PRESETS) + 1)

    for i, (preset_key, preset) in enumerate(CONSTRAINT_PRESETS.items()):
        lang = st.session_state.get("language", "ja")
        name = preset.get(f"name_{lang}", preset.get("name_ja", preset_key))
        desc = preset.get(f"description_{lang}", preset.get("description_ja", ""))

        with cols[i]:
            if st.button(name, key=f"preset_{preset_key}", use_container_width=True,
                        help=desc):
                if ConstraintService.apply_preset(branch_id, preset_key):
                    st.success(t("common.success"))
                    st.rerun()
                else:
                    st.error(t("errors.generic"))

    with cols[-1]:
        if st.button(t("common.reset"), key="reset_presets", use_container_width=True):
            # 기본값으로 초기화
            constraints = ConstraintService.get_all_constraints(branch_id)
            for c in constraints:
                ConstraintService.delete_constraint(c.id)
            ConstraintService.init_default_constraints(branch_id)
            st.success(t("common.success"))
            st.rerun()


def render_constraint_list(branch_id: str, can_edit: bool):
    """제약 목록 렌더링"""
    constraints = ConstraintService.get_all_constraints(branch_id)

    if not constraints:
        # 기본 제약 초기화
        if can_edit:
            if st.button(t("common.add") + " " + t("constraints.title")):
                ConstraintService.init_default_constraints(branch_id)
                st.rerun()
        st.info(t("common.none"))
        return

    # 카테고리별 탭
    lang = st.session_state.get("language", "ja")
    categories = list(CONSTRAINT_CATEGORIES.keys())
    category_names = [CONSTRAINT_CATEGORIES[c].get(f"name_{lang}", c) for c in categories]

    tabs = st.tabs([t("common.all")] + category_names)

    # 전체 탭
    with tabs[0]:
        render_constraints_table(constraints, can_edit, lang, "all")

    # 카테고리별 탭
    for i, category in enumerate(categories):
        with tabs[i + 1]:
            filtered = [c for c in constraints if c.category == category]
            if filtered:
                render_constraints_table(filtered, can_edit, lang, category)
            else:
                st.info(t("common.none"))


def render_constraints_table(constraints: list, can_edit: bool, lang: str, key_prefix: str = ""):
    """제약 테이블 렌더링"""
    for constraint in constraints:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 1])

            with col1:
                # 이름 및 설명
                desc = constraint.get_description(lang)
                type_badge = "🔴" if constraint.is_hard() else "🟡"
                enabled_badge = "✓" if constraint.is_enabled else "✗"

                st.markdown(f"**{type_badge} {constraint.name}** {enabled_badge}")
                st.caption(desc)

            with col2:
                # 카테고리
                cat_name = CONSTRAINT_CATEGORIES.get(constraint.category, {}).get(f"name_{lang}", constraint.category)
                st.caption(cat_name)

            with col3:
                # 타입
                type_name = t("constraints.hard_constraints") if constraint.is_hard() else t("constraints.soft_constraints")
                st.caption(type_name)

            with col4:
                # 가중치 슬라이더 (소프트 제약만)
                if can_edit and constraint.is_soft():
                    new_weight = st.slider(
                        t("constraints.weight"),
                        min_value=0,
                        max_value=200000,
                        value=constraint.penalty_weight,
                        step=1000,
                        key=f"weight_{key_prefix}_{constraint.id}",
                        label_visibility="collapsed"
                    )
                    if new_weight != constraint.penalty_weight:
                        ConstraintService.update_weight(constraint.id, new_weight)
                else:
                    st.caption(f"{t('constraints.weight')}: {constraint.penalty_weight}")

            with col5:
                # 활성화 토글
                if can_edit:
                    enabled = st.toggle(
                        t("constraints.enabled"),
                        value=constraint.is_enabled,
                        key=f"toggle_{key_prefix}_{constraint.id}",
                        label_visibility="collapsed"
                    )
                    if enabled != constraint.is_enabled:
                        ConstraintService.update_constraint(constraint.id, is_enabled=enabled)
                        st.rerun()

            st.divider()


def render_add_constraint(branch_id: str):
    """제약 추가 폼"""
    with st.expander(t("constraints.add_constraint"), expanded=False):
        with st.form("add_constraint_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(t("constraints.name"))
                code = st.text_input(t("constraints.code"))
                lang = st.session_state.get("language", "ja")
                category = st.selectbox(
                    t("constraints.category"),
                    options=list(CONSTRAINT_CATEGORIES.keys()),
                    format_func=lambda x: CONSTRAINT_CATEGORIES[x].get(f"name_{lang}", x)
                )

            with col2:
                constraint_type = st.selectbox(
                    t("constraints.type"),
                    options=["hard", "soft"],
                    format_func=lambda x: t("constraints.hard_constraints") if x == "hard" else t("constraints.soft_constraints")
                )
                weight = st.number_input(
                    t("constraints.weight"),
                    min_value=0,
                    max_value=200000,
                    value=10000,
                    step=1000
                )
                priority = st.number_input(
                    t("constraints.priority"),
                    min_value=1,
                    max_value=100,
                    value=50
                )

            description = st.text_area(
                t("common.info"),
                placeholder="Description for this constraint..."
            )

            submitted = st.form_submit_button(t("common.add"))

            if submitted:
                if not name or not code:
                    st.error(t("errors.validation"))
                    return

                constraint_data = {
                    "name": name,
                    "code": code,
                    "category": category,
                    "constraint_type": constraint_type,
                    "penalty_weight": weight,
                    "priority_order": priority,
                    "is_enabled": True,
                    "rule_definition": {
                        "type": "basic",
                        "description_ja": description,
                        "description_ko": description,
                        "description_en": description,
                        "rule": {}
                    }
                }

                result = ConstraintService.create_constraint(branch_id, constraint_data)
                if result:
                    st.success(t("common.success"))
                    st.rerun()
                else:
                    st.error(t("errors.save_failed"))


def render_export_import(branch_id: str):
    """내보내기/가져오기"""
    col1, col2 = st.columns(2)

    with col1:
        if st.button(t("constraints.export_json"), use_container_width=True):
            json_str = ConstraintService.export_constraints(branch_id)
            st.download_button(
                label=t("common.export"),
                data=json_str,
                file_name="constraints.json",
                mime="application/json"
            )

    with col2:
        uploaded = st.file_uploader(t("constraints.import_json"), type=["json"])
        if uploaded:
            json_str = uploaded.read().decode("utf-8")
            if st.button(t("common.import")):
                if ConstraintService.import_constraints(branch_id, json_str, replace=False):
                    st.success(t("common.success"))
                    st.rerun()
