# pages/constraints.py
"""제약 조건 관리 페이지"""

import streamlit as st
from localization import t
from core.session import get_current_branch_id, get_current_branch_name
from core.auth import is_editor, is_super
from services.constraint_service import ConstraintService
from config.constants import CONSTRAINT_CATEGORIES
from config.default_constraints import CONSTRAINT_PRESETS, AVAILABLE_CONSTRAINT_TEMPLATES, CONSTRAINT_RULE_TYPES
import json


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
    """제약 추가 폼 - 템플릿 선택 / 직접 입력 모드"""
    lang = st.session_state.get("language", "ja")

    with st.expander(t("constraints.add_constraint"), expanded=False):
        # 모드 선택 탭
        tab_template, tab_custom = st.tabs(["📋 템플릿에서 선택", "✏️ 직접 입력"])

        # === 템플릿 선택 모드 ===
        with tab_template:
            render_template_mode(branch_id, lang)

        # === 직접 입력 모드 ===
        with tab_custom:
            render_custom_mode(branch_id, lang)


def render_template_mode(branch_id: str, lang: str):
    """템플릿 선택 모드"""
    # 템플릿 드롭다운
    template_options = {t["template_id"]: t for t in AVAILABLE_CONSTRAINT_TEMPLATES}

    # 카테고리별 그룹핑
    name_key = f"name_{lang}" if lang in ["ko", "ja"] else "name_ko"
    template_names = {
        t["template_id"]: f"[{CONSTRAINT_CATEGORIES.get(t['category'], {}).get(f'name_{lang}', t['category'])}] {t.get(name_key, t['name_ko'])}"
        for t in AVAILABLE_CONSTRAINT_TEMPLATES
    }

    selected_template_id = st.selectbox(
        "제약 템플릿 선택",
        options=list(template_options.keys()),
        format_func=lambda x: template_names.get(x, x),
        key="template_select"
    )

    if selected_template_id:
        template = template_options[selected_template_id]

        # 템플릿 정보 표시
        st.info(f"**{template.get(name_key, template['name_ko'])}**\n\n{template.get('description_ko', '')}")

        col1, col2 = st.columns(2)
        with col1:
            cat_name = CONSTRAINT_CATEGORIES.get(template["category"], {}).get(f"name_{lang}", template["category"])
            type_name = "하드 (필수)" if template["constraint_type"] == "hard" else "소프트 (선호)"
            st.markdown(f"- **카테고리**: {cat_name}")
            st.markdown(f"- **타입**: {type_name}")
        with col2:
            st.markdown(f"- **기본 가중치**: {template['default_weight']:,}")

        st.divider()

        # 편집 가능한 파라미터
        param_values = {}
        if template.get("editable_params"):
            st.markdown("**파라미터 설정**")
            for param in template["editable_params"]:
                key = param["key"]
                label = param.get("label_ko", key)

                if param["type"] == "number":
                    param_values[key] = st.number_input(
                        label,
                        min_value=param.get("min", 0),
                        max_value=param.get("max", 200000),
                        value=param.get("default", 0),
                        key=f"tpl_param_{selected_template_id}_{key}"
                    )
                elif param["type"] == "text":
                    param_values[key] = st.text_input(
                        label,
                        value=str(param.get("default", "")),
                        key=f"tpl_param_{selected_template_id}_{key}"
                    )
                elif param["type"] == "bool":
                    param_values[key] = st.checkbox(
                        label,
                        value=param.get("default", False),
                        key=f"tpl_param_{selected_template_id}_{key}"
                    )

        # 추가 버튼
        if st.button(t("common.add"), key="add_from_template", use_container_width=True, type="primary"):
            # rule_definition 구성
            rule_def = template["rule_definition"].copy()
            rule = rule_def.get("rule", {}).copy()

            # 파라미터 적용
            weight = template["default_weight"]
            for key, value in param_values.items():
                if key == "penalty_weight":
                    weight = value
                elif key in ["after_shifts", "balance_shifts"]:
                    # 쉼표 구분 텍스트를 리스트로 변환
                    rule[key] = [s.strip() for s in value.split(",") if s.strip()]
                else:
                    rule[key] = value

            rule_def["rule"] = rule
            rule_def["description_ja"] = template.get("name_ja", template["name_ko"])
            rule_def["description_ko"] = template.get("name_ko", "")
            rule_def["description_en"] = template.get("name_ko", "")

            # 제약 생성
            import uuid
            constraint_data = {
                "name": template.get(f"name_{lang}", template["name_ko"]),
                "code": f"{template['template_id'].upper()}_{str(uuid.uuid4())[:4]}",
                "category": template["category"],
                "constraint_type": template["constraint_type"],
                "penalty_weight": weight,
                "priority_order": 50,
                "is_enabled": True,
                "rule_definition": rule_def
            }

            result = ConstraintService.create_constraint(branch_id, constraint_data)
            if result:
                st.success(t("common.success"))
                st.rerun()
            else:
                st.error(t("errors.save_failed"))


def render_custom_mode(branch_id: str, lang: str):
    """직접 입력 모드"""
    with st.form("add_constraint_form_custom"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(t("constraints.name"))
            code = st.text_input(t("constraints.code"))
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

        st.divider()
        st.markdown("**규칙 정의**")

        # rule_type 드롭다운
        rule_type = st.selectbox(
            "규칙 타입",
            options=list(CONSTRAINT_RULE_TYPES.keys()),
            format_func=lambda x: f"{CONSTRAINT_RULE_TYPES[x].get(f'name_{lang}', x)} - {CONSTRAINT_RULE_TYPES[x].get('description_ko', '')}"
        )

        # 선택된 rule_type에 따른 파라미터 입력
        rule_params = {}
        rule_type_info = CONSTRAINT_RULE_TYPES.get(rule_type, {})

        if rule_type_info.get("params"):
            st.caption("규칙 파라미터")
            param_cols = st.columns(2)
            for i, param in enumerate(rule_type_info["params"]):
                key = param["key"]
                label = param.get("label_ko", key)

                with param_cols[i % 2]:
                    if param["type"] == "number":
                        rule_params[key] = st.number_input(
                            label,
                            min_value=param.get("min", 0),
                            max_value=param.get("max", 200000),
                            value=param.get("default", 0),
                            key=f"custom_param_{key}"
                        )
                    elif param["type"] == "text":
                        rule_params[key] = st.text_input(
                            label,
                            value=str(param.get("default", "")),
                            key=f"custom_param_{key}"
                        )
                    elif param["type"] == "bool":
                        rule_params[key] = st.checkbox(
                            label,
                            value=param.get("default", False),
                            key=f"custom_param_{key}"
                        )
                    elif param["type"] == "json":
                        json_str = st.text_area(
                            label,
                            value=param.get("default", "{}"),
                            key=f"custom_param_{key}"
                        )
                        try:
                            rule_params[key] = json.loads(json_str)
                        except:
                            rule_params[key] = {}

        description = st.text_area(
            t("common.info"),
            placeholder="제약 설명..."
        )

        submitted = st.form_submit_button(t("common.add"), use_container_width=True)

        if submitted:
            if not name or not code:
                st.error(t("errors.validation"))
                return

            # rule 파라미터 정리
            rule = {}
            for key, value in rule_params.items():
                if value:  # 빈 값 제외
                    if key in ["after_shifts", "balance_shifts", "next_day_must_be"]:
                        # 쉼표 구분 텍스트를 리스트로
                        if isinstance(value, str):
                            rule[key] = [s.strip() for s in value.split(",") if s.strip()]
                        else:
                            rule[key] = value
                    else:
                        rule[key] = value

            constraint_data = {
                "name": name,
                "code": code,
                "category": category,
                "constraint_type": constraint_type,
                "penalty_weight": weight,
                "priority_order": priority,
                "is_enabled": True,
                "rule_definition": {
                    "type": rule_type,
                    "description_ja": description,
                    "description_ko": description,
                    "description_en": description,
                    "rule": rule
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
