# components/mobile_nav.py
"""모바일 네비게이션 컴포넌트"""

import streamlit as st
from localization import t
from config.constants import PAGES
from core.session import get_current_page, set_current_page


def inject_mobile_css():
    """모바일 반응형 CSS 주입"""
    st.markdown("""
    <style>
    /* 모바일 하단 네비게이션 */
    @media (max-width: 768px) {
        /* 사이드바 숨기기 */
        [data-testid="stSidebar"] {
            display: none !important;
        }

        /* 메인 컨텐츠 여백 조정 */
        .main .block-container {
            padding-bottom: 80px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* 하단 네비게이션 바 */
        .mobile-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: var(--background-color, #ffffff);
            border-top: 1px solid var(--secondary-background-color, #f0f2f6);
            display: flex;
            justify-content: space-around;
            align-items: center;
            z-index: 999;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        }

        .mobile-nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 8px;
            cursor: pointer;
            color: var(--text-color, #262730);
            text-decoration: none;
            font-size: 10px;
            transition: all 0.2s;
        }

        .mobile-nav-item:hover,
        .mobile-nav-item.active {
            color: var(--primary-color, #ff4b4b);
        }

        .mobile-nav-item .icon {
            font-size: 20px;
            margin-bottom: 2px;
        }

        /* 테이블 반응형 */
        .stDataFrame {
            font-size: 12px !important;
        }

        /* 버튼 터치 영역 확대 */
        .stButton button {
            min-height: 44px;
            padding: 10px 16px;
        }

        /* 입력 필드 터치 영역 */
        .stTextInput input,
        .stSelectbox select,
        .stNumberInput input {
            min-height: 44px;
            font-size: 16px;
        }
    }

    /* 태블릿 */
    @media (min-width: 769px) and (max-width: 1024px) {
        [data-testid="stSidebar"] {
            width: 200px !important;
        }

        .main .block-container {
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
    }

    /* 데스크톱 - 하단 네비 숨기기 */
    @media (min-width: 769px) {
        .mobile-nav {
            display: none !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def render_mobile_nav():
    """모바일 하단 네비게이션 렌더링"""
    current_page = get_current_page()
    lang = st.session_state.get("language", "ja")

    # 모바일에서 표시할 주요 페이지
    mobile_pages = ["dashboard", "schedule", "staff", "constraints", "settings"]

    nav_items = []
    for page_key in mobile_pages:
        if page_key in PAGES:
            page_info = PAGES[page_key]
            name = page_info.get(f"name_{lang}", page_info.get("name_ja", page_key))
            icon = page_info.get("icon", "📄")
            is_active = "active" if page_key == current_page else ""

            nav_items.append(f'''
                <div class="mobile-nav-item {is_active}" onclick="handleNavClick('{page_key}')">
                    <span class="icon">{icon}</span>
                    <span>{name}</span>
                </div>
            ''')

    nav_html = f'''
    <div class="mobile-nav">
        {''.join(nav_items)}
    </div>

    <script>
    function handleNavClick(page) {{
        // Streamlit에 페이지 변경 요청
        const form = document.createElement('form');
        form.method = 'post';
        form.action = '';

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'mobile_nav_page';
        input.value = page;
        form.appendChild(input);

        document.body.appendChild(form);
        form.submit();
    }}
    </script>
    '''

    st.markdown(nav_html, unsafe_allow_html=True)

    # Streamlit 네이티브 방식으로 페이지 변경 처리
    # (JavaScript 폼 제출이 동작하지 않을 수 있으므로 대안 제공)


def render_mobile_header(title: str, show_back: bool = False, on_back=None):
    """모바일 헤더 렌더링"""
    col1, col2, col3 = st.columns([1, 4, 1])

    with col1:
        if show_back:
            if st.button("←", key="mobile_back"):
                if on_back:
                    on_back()
                else:
                    set_current_page("dashboard")
                    st.rerun()

    with col2:
        st.markdown(f"<h3 style='text-align: center; margin: 0;'>{title}</h3>",
                   unsafe_allow_html=True)

    with col3:
        # 알림 아이콘 등 추가 가능
        pass


def is_mobile_view() -> bool:
    """모바일 뷰 여부 확인 (JavaScript 필요, 여기서는 근사치)"""
    # Streamlit에서는 클라이언트 정보를 직접 얻기 어려움
    # 대신 session state로 관리하거나 JS로 감지 후 설정
    return st.session_state.get("is_mobile", False)


def detect_mobile_view():
    """모바일 뷰 감지 스크립트 주입"""
    st.markdown("""
    <script>
    (function() {
        const isMobile = window.innerWidth <= 768;
        // Streamlit에 전달하는 방법이 제한적이므로
        // 주로 CSS 미디어 쿼리로 처리
    })();
    </script>
    """, unsafe_allow_html=True)
