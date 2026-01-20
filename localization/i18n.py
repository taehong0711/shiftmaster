# localization/i18n.py
"""다국어 지원 모듈"""

import json
import os
import streamlit as st
from typing import Dict, Any, Optional
from functools import lru_cache

from config.constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


# 번역 캐시
_translations_cache: Dict[str, Dict[str, Any]] = {}


def get_translations_dir() -> str:
    """번역 파일 디렉토리 경로"""
    return os.path.join(os.path.dirname(__file__), "translations")


@lru_cache(maxsize=10)
def load_translations(lang: str) -> Dict[str, Any]:
    """번역 파일 로드"""
    if lang in _translations_cache:
        return _translations_cache[lang]

    translations_dir = get_translations_dir()
    file_path = os.path.join(translations_dir, f"{lang}.json")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
            _translations_cache[lang] = translations
            return translations
    except FileNotFoundError:
        # 기본 언어로 폴백
        if lang != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}
    except json.JSONDecodeError as e:
        st.warning(f"번역 파일 파싱 오류 ({lang}): {e}")
        return {}


def get_nested_value(data: Dict[str, Any], key: str) -> Optional[str]:
    """점으로 구분된 키로 중첩 딕셔너리 값 가져오기

    예: get_nested_value(data, "dashboard.title") -> data["dashboard"]["title"]
    """
    keys = key.split(".")
    current = data

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None

    return current if isinstance(current, str) else None


def t(key: str, **kwargs) -> str:
    """번역 함수

    Args:
        key: 번역 키 (점으로 구분, 예: "dashboard.title")
        **kwargs: 문자열 포맷팅 변수

    Returns:
        번역된 문자열. 찾지 못하면 키 반환.

    Example:
        t("dashboard.title")  # -> "ダッシュボード"
        t("common.items_count", count=5)  # -> "5 items"
    """
    # 현재 언어 가져오기
    lang = st.session_state.get("language", DEFAULT_LANGUAGE)

    # 번역 로드
    translations = load_translations(lang)

    # 값 가져오기
    value = get_nested_value(translations, key)

    if value is None:
        # 기본 언어로 폴백
        if lang != DEFAULT_LANGUAGE:
            fallback_translations = load_translations(DEFAULT_LANGUAGE)
            value = get_nested_value(fallback_translations, key)

    if value is None:
        # 키 그대로 반환
        return key

    # 변수 치환
    if kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value

    return value


def t_list(key: str) -> list:
    """리스트 형태의 번역 값 가져오기"""
    lang = st.session_state.get("language", DEFAULT_LANGUAGE)
    translations = load_translations(lang)

    keys = key.split(".")
    current = translations

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return []

    return current if isinstance(current, list) else []


def get_current_language() -> str:
    """현재 언어 코드 반환"""
    return st.session_state.get("language", DEFAULT_LANGUAGE)


def set_language(lang: str):
    """언어 설정"""
    if lang in SUPPORTED_LANGUAGES:
        st.session_state.language = lang


def get_language_name(lang_code: str = None) -> str:
    """언어 이름 반환"""
    if lang_code is None:
        lang_code = get_current_language()
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


def get_available_languages() -> Dict[str, str]:
    """사용 가능한 언어 목록"""
    return SUPPORTED_LANGUAGES.copy()


def format_date(date_obj, format_key: str = "date_format") -> str:
    """날짜 형식화"""
    format_str = t(f"common.{format_key}")
    if format_str == f"common.{format_key}":
        format_str = "%Y-%m-%d"  # 기본 형식
    return date_obj.strftime(format_str)


def format_number(number: float, decimals: int = 0) -> str:
    """숫자 형식화 (로케일 기반)"""
    lang = get_current_language()

    if decimals == 0:
        return f"{int(number):,}"
    return f"{number:,.{decimals}f}"


class TranslationContext:
    """번역 컨텍스트 (임시 언어 변경용)"""

    def __init__(self, lang: str):
        self.new_lang = lang
        self.old_lang = None

    def __enter__(self):
        self.old_lang = get_current_language()
        set_language(self.new_lang)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_lang:
            set_language(self.old_lang)
        return False


# 편의 함수 별칭
_ = t  # 짧은 별칭
translate = t
