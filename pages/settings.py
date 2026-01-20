# pages/settings.py
"""설정 페이지"""

import streamlit as st
import json
from localization import t, set_language, get_available_languages, get_current_language
from core.session import (
    get_session, set_session, get_theme, set_theme, toggle_theme,
    increment_cache_version
)
from core.auth import get_current_user, get_current_role, logout, is_super
from config.constants import DEFAULT_DAY_SHIFTS, DEFAULT_NIGHT_SHIFTS


def render():
    """설정 페이지 렌더링"""
    st.title(t("settings.title"))

    # 탭 구성
    tabs = st.tabs([
        t("settings.general"),
        t("settings.appearance"),
        t("settings.shift_codes"),
        t("settings.account"),
        t("settings.data_management")
    ])

    with tabs[0]:
        render_general_settings()

    with tabs[1]:
        render_appearance_settings()

    with tabs[2]:
        render_shift_code_settings()

    with tabs[3]:
        render_account_settings()

    with tabs[4]:
        if is_super():
            render_data_management()
        else:
            st.info(t("auth.access_denied"))


def render_general_settings():
    """일반 설정"""
    st.subheader(t("settings.general"))

    # 언어 선택
    languages = get_available_languages()
    current_lang = get_current_language()

    selected_lang = st.selectbox(
        t("settings.language"),
        options=list(languages.keys()),
        format_func=lambda x: languages[x],
        index=list(languages.keys()).index(current_lang) if current_lang in languages else 0
    )

    if selected_lang != current_lang:
        set_language(selected_lang)
        st.success(t("common.success"))
        st.rerun()


def render_appearance_settings():
    """외관 설정"""
    st.subheader(t("settings.appearance"))

    # 테마 선택
    current_theme = get_theme()

    theme_options = {
        "light": t("settings.light_mode"),
        "dark": t("settings.dark_mode")
    }

    selected_theme = st.radio(
        t("settings.theme"),
        options=list(theme_options.keys()),
        format_func=lambda x: theme_options[x],
        index=0 if current_theme == "light" else 1,
        horizontal=True
    )

    if selected_theme != current_theme:
        set_theme(selected_theme)
        st.success(t("common.success"))
        st.rerun()

    # 참고: Streamlit의 실제 테마는 .streamlit/config.toml에서 설정해야 함
    st.info("Note: Full theme support requires config.toml configuration")


def render_shift_code_settings():
    """시프트 코드 설정"""
    st.subheader(t("settings.shift_codes"))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{t('settings.day_shifts')}**")
        day_shifts = get_session("shifts_day", DEFAULT_DAY_SHIFTS)
        day_shifts_str = st.text_input(
            t("settings.day_shifts"),
            value=",".join(day_shifts),
            label_visibility="collapsed"
        )
        new_day_shifts = [s.strip() for s in day_shifts_str.split(",") if s.strip()]

    with col2:
        st.markdown(f"**{t('settings.night_shifts')}**")
        night_shifts = get_session("shifts_night", DEFAULT_NIGHT_SHIFTS)
        night_shifts_str = st.text_input(
            t("settings.night_shifts"),
            value=",".join(night_shifts),
            label_visibility="collapsed"
        )
        new_night_shifts = [s.strip() for s in night_shifts_str.split(",") if s.strip()]

    if st.button(t("common.save"), key="save_shifts"):
        set_session("shifts_day", new_day_shifts)
        set_session("shifts_night", new_night_shifts)
        st.success(t("common.success"))

    # 현재 설정 표시
    st.divider()
    st.markdown("**Current Configuration:**")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"{t('settings.day_shifts')}: {', '.join(new_day_shifts)}")
    with col2:
        st.write(f"{t('settings.night_shifts')}: {', '.join(new_night_shifts)}")


def render_account_settings():
    """계정 설정"""
    st.subheader(t("settings.account"))

    user = get_current_user()
    role = get_current_role()

    col1, col2 = st.columns(2)

    with col1:
        st.metric(t("settings.current_user"), user or "-")

    with col2:
        role_display = {
            "super": "Super Admin",
            "editor": "Editor",
            "viewer": "Viewer"
        }.get(role, role or "-")
        st.metric(t("settings.current_role"), role_display)

    st.divider()

    if st.button(t("auth.logout_button"), type="primary"):
        logout()
        st.success(t("common.success"))
        st.rerun()


def render_data_management():
    """데이터 관리 (super only)"""
    st.subheader(t("settings.data_management"))

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(t("settings.clear_cache"), use_container_width=True):
            increment_cache_version()
            st.cache_data.clear()
            st.success(t("common.success"))

    with col2:
        if st.button(t("settings.export_settings"), use_container_width=True):
            settings_data = {
                "language": get_current_language(),
                "theme": get_theme(),
                "shifts_day": get_session("shifts_day", DEFAULT_DAY_SHIFTS),
                "shifts_night": get_session("shifts_night", DEFAULT_NIGHT_SHIFTS),
            }
            json_str = json.dumps(settings_data, ensure_ascii=False, indent=2)
            st.download_button(
                label=t("common.export"),
                data=json_str,
                file_name="settings.json",
                mime="application/json"
            )

    with col3:
        if st.button(t("settings.reset_defaults"), use_container_width=True):
            set_session("shifts_day", DEFAULT_DAY_SHIFTS)
            set_session("shifts_night", DEFAULT_NIGHT_SHIFTS)
            set_language("ja")
            set_theme("light")
            st.success(t("common.success"))
            st.rerun()

    st.divider()

    # 설정 가져오기
    uploaded = st.file_uploader(t("settings.import_settings"), type=["json"])
    if uploaded:
        try:
            settings = json.loads(uploaded.read().decode("utf-8"))
            if st.button(t("common.import")):
                if "language" in settings:
                    set_language(settings["language"])
                if "theme" in settings:
                    set_theme(settings["theme"])
                if "shifts_day" in settings:
                    set_session("shifts_day", settings["shifts_day"])
                if "shifts_night" in settings:
                    set_session("shifts_night", settings["shifts_night"])
                st.success(t("common.success"))
                st.rerun()
        except Exception as e:
            st.error(f"{t('errors.generic')}: {e}")
