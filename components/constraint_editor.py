# components/constraint_editor.py
"""제약 조건 편집 위젯"""

import streamlit as st
from typing import Optional, Callable
from localization import t
from models.constraint import Constraint
from services.constraint_service import ConstraintService
from config.constants import CONSTRAINT_CATEGORIES


def render_constraint_editor(
    constraint: Constraint,
    on_save: Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
    lang: str = "ja"
):
    """
    제약 조건 편집 위젯

    Args:
        constraint: 편집할 제약 조건
        on_save: 저장 시 콜백
        on_delete: 삭제 시 콜백
        lang: 언어 코드
    """
    with st.container():
        # 헤더
        col_header, col_toggle = st.columns([4, 1])

        with col_header:
            type_icon = "🔴" if constraint.is_hard() else "🟡"
            st.markdown(f"### {type_icon} {constraint.name}")

        with col_toggle:
            enabled = st.toggle(
                t("constraints.enabled"),
                value=constraint.is_enabled,
                key=f"edit_toggle_{constraint.id}"
            )

        # 설명
        desc = constraint.get_description(lang)
        st.caption(desc)

        st.divider()

        # 편집 폼
        col1, col2 = st.columns(2)

        with col1:
            # 카테고리
            category_options = list(CONSTRAINT_CATEGORIES.keys())
            category_idx = category_options.index(constraint.category) if constraint.category in category_options else 0

            new_category = st.selectbox(
                t("constraints.category"),
                options=category_options,
                index=category_idx,
                format_func=lambda x: CONSTRAINT_CATEGORIES[x].get(f"name_{lang}", x),
                key=f"edit_cat_{constraint.id}"
            )

            # 타입
            type_options = ["hard", "soft"]
            type_idx = 0 if constraint.is_hard() else 1

            new_type = st.selectbox(
                t("constraints.type"),
                options=type_options,
                index=type_idx,
                format_func=lambda x: t("constraints.hard_constraints") if x == "hard" else t("constraints.soft_constraints"),
                key=f"edit_type_{constraint.id}"
            )

        with col2:
            # 가중치 (소프트 제약만)
            if new_type == "soft":
                new_weight = st.slider(
                    t("constraints.weight"),
                    min_value=0,
                    max_value=200000,
                    value=constraint.penalty_weight,
                    step=1000,
                    key=f"edit_weight_{constraint.id}"
                )
            else:
                new_weight = constraint.penalty_weight
                st.info(f"{t('constraints.weight')}: N/A (Hard)")

            # 우선순위
            new_priority = st.number_input(
                t("constraints.priority"),
                min_value=1,
                max_value=100,
                value=constraint.priority_order,
                key=f"edit_priority_{constraint.id}"
            )

        # 규칙 정의 (JSON 에디터)
        with st.expander("Rule Definition (JSON)", expanded=False):
            import json
            rule_json = json.dumps(constraint.rule_definition, ensure_ascii=False, indent=2)
            new_rule_json = st.text_area(
                "JSON",
                value=rule_json,
                height=200,
                key=f"edit_rule_{constraint.id}"
            )

        st.divider()

        # 버튼
        col_save, col_delete, col_cancel = st.columns(3)

        with col_save:
            if st.button(t("common.save"), key=f"save_{constraint.id}", use_container_width=True,
                        type="primary"):
                try:
                    import json
                    new_rule = json.loads(new_rule_json)

                    success = ConstraintService.update_constraint(
                        constraint.id,
                        category=new_category,
                        constraint_type=new_type,
                        penalty_weight=new_weight,
                        priority_order=new_priority,
                        is_enabled=enabled,
                        rule_definition=new_rule
                    )

                    if success:
                        st.success(t("common.success"))
                        if on_save:
                            on_save(constraint)
                    else:
                        st.error(t("errors.save_failed"))
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")

        with col_delete:
            if st.button(t("common.delete"), key=f"delete_{constraint.id}", use_container_width=True):
                if on_delete:
                    on_delete(constraint)

        with col_cancel:
            if st.button(t("common.cancel"), key=f"cancel_{constraint.id}", use_container_width=True):
                st.rerun()


def render_constraint_card(constraint: Constraint, can_edit: bool = False, lang: str = "ja"):
    """
    제약 조건 카드 (읽기 전용 또는 간단한 토글)

    Args:
        constraint: 제약 조건
        can_edit: 편집 가능 여부
        lang: 언어 코드
    """
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            type_icon = "🔴" if constraint.is_hard() else "🟡"
            enabled_icon = "✓" if constraint.is_enabled else "✗"
            st.markdown(f"**{type_icon} {constraint.name}** {enabled_icon}")

            desc = constraint.get_description(lang)
            st.caption(desc)

        with col2:
            if constraint.is_soft():
                st.caption(f"Weight: {constraint.penalty_weight:,}")
            else:
                st.caption("Hard")

        with col3:
            if can_edit:
                new_enabled = st.toggle(
                    "",
                    value=constraint.is_enabled,
                    key=f"card_toggle_{constraint.id}"
                )
                if new_enabled != constraint.is_enabled:
                    ConstraintService.toggle_constraint(constraint.id)
                    st.rerun()
