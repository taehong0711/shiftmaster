# components/priority_slider.py
"""우선순위 슬라이더 위젯"""

import streamlit as st
from typing import List, Callable, Optional
from localization import t


def render_priority_slider(
    item_id: str,
    label: str,
    current_value: int,
    min_value: int = 0,
    max_value: int = 200000,
    step: int = 1000,
    on_change: Optional[Callable[[int], None]] = None,
    show_presets: bool = True
):
    """
    가중치 슬라이더 렌더링

    Args:
        item_id: 고유 ID
        label: 라벨
        current_value: 현재 값
        min_value: 최소값
        max_value: 최대값
        step: 단계
        on_change: 값 변경 시 콜백
        show_presets: 프리셋 버튼 표시 여부
    """
    with st.container():
        st.caption(label)

        col1, col2 = st.columns([4, 1])

        with col1:
            new_value = st.slider(
                label,
                min_value=min_value,
                max_value=max_value,
                value=current_value,
                step=step,
                key=f"priority_slider_{item_id}",
                label_visibility="collapsed"
            )

        with col2:
            st.markdown(f"**{new_value:,}**")

        # 프리셋 버튼
        if show_presets:
            presets = [
                ("Low", 1000),
                ("Med", 10000),
                ("High", 50000),
                ("Max", 100000),
            ]

            cols = st.columns(len(presets))
            for i, (preset_name, preset_value) in enumerate(presets):
                with cols[i]:
                    if st.button(
                        preset_name,
                        key=f"preset_{item_id}_{preset_name}",
                        use_container_width=True,
                        type="secondary" if preset_value != current_value else "primary"
                    ):
                        new_value = preset_value
                        if on_change:
                            on_change(preset_value)

        # 값 변경 감지
        if new_value != current_value and on_change:
            on_change(new_value)

        return new_value


def render_priority_list(
    items: List[dict],
    on_reorder: Optional[Callable[[List[str]], None]] = None,
    on_weight_change: Optional[Callable[[str, int], None]] = None
):
    """
    우선순위 리스트 렌더링 (드래그 앤 드롭 대체)

    Args:
        items: [{"id": str, "name": str, "weight": int, "priority": int}, ...]
        on_reorder: 순서 변경 시 콜백
        on_weight_change: 가중치 변경 시 콜백
    """
    st.caption(t("constraints.priority_drag"))

    # 정렬된 아이템
    sorted_items = sorted(items, key=lambda x: x.get("priority", 50))

    for i, item in enumerate(sorted_items):
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 3, 3, 1])

            with col1:
                st.markdown(f"**{i + 1}**")

            with col2:
                st.markdown(f"**{item['name']}**")

            with col3:
                new_weight = st.slider(
                    t("constraints.weight"),
                    min_value=0,
                    max_value=200000,
                    value=item.get("weight", 10000),
                    step=1000,
                    key=f"list_weight_{item['id']}",
                    label_visibility="collapsed"
                )

                if new_weight != item.get("weight") and on_weight_change:
                    on_weight_change(item["id"], new_weight)

            with col4:
                # 위/아래 이동 버튼
                col_up, col_down = st.columns(2)
                with col_up:
                    if i > 0:
                        if st.button("↑", key=f"up_{item['id']}", use_container_width=True):
                            # 순서 변경
                            new_order = [it["id"] for it in sorted_items]
                            new_order[i], new_order[i-1] = new_order[i-1], new_order[i]
                            if on_reorder:
                                on_reorder(new_order)
                with col_down:
                    if i < len(sorted_items) - 1:
                        if st.button("↓", key=f"down_{item['id']}", use_container_width=True):
                            new_order = [it["id"] for it in sorted_items]
                            new_order[i], new_order[i+1] = new_order[i+1], new_order[i]
                            if on_reorder:
                                on_reorder(new_order)

            st.divider()


def render_weight_comparison(items: List[dict], lang: str = "ja"):
    """
    가중치 비교 시각화

    Args:
        items: [{"name": str, "weight": int}, ...]
        lang: 언어 코드
    """
    import plotly.graph_objects as go

    if not items:
        st.info(t("common.none"))
        return

    # 정렬
    sorted_items = sorted(items, key=lambda x: x.get("weight", 0), reverse=True)

    names = [item["name"] for item in sorted_items]
    weights = [item.get("weight", 0) for item in sorted_items]

    fig = go.Figure(go.Bar(
        x=weights,
        y=names,
        orientation='h',
        marker_color=['#F44336' if w > 50000 else '#FFC107' if w > 10000 else '#4CAF50'
                     for w in weights]
    ))

    fig.update_layout(
        title=t("constraints.weight"),
        xaxis_title=t("constraints.weight"),
        yaxis_title="",
        height=max(200, len(items) * 30),
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
