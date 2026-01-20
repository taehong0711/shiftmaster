# pages/requests_page.py
"""희망/NG 입력 페이지"""

import streamlit as st
import pandas as pd
from datetime import date
from calendar import monthrange
from localization import t
from core.session import get_current_branch_id, get_session, set_session
from core.auth import is_editor
from models.staff import get_staff_for_branch
from config.constants import DEFAULT_DAY_SHIFTS, DEFAULT_NIGHT_SHIFTS, SHIFT_OFF, SHIFT_PUBLIC_OFF


def render():
    """희망/NG 입력 페이지 렌더링"""
    st.title(t("requests.title"))

    branch_id = get_current_branch_id()
    if not branch_id:
        st.warning(t("branches.no_branches"))
        return

    can_edit = is_editor()

    # 대상 월 설정
    col1, col2 = st.columns([1, 3])
    with col1:
        today = date.today()
        next_month = date(today.year + (today.month // 12), (today.month % 12) + 1, 1)
        target_date = st.date_input(
            t("schedule.target_month"),
            value=next_month
        )
        year = target_date.year
        month = target_date.month
        num_days = monthrange(year, month)[1]

    st.divider()

    # 탭 구성
    tabs = st.tabs([
        t("requests.request_input"),
        t("requests.ng_input"),
        t("schedule.previous_history")
    ])

    with tabs[0]:
        render_requests_input(branch_id, year, month, num_days, can_edit)

    with tabs[1]:
        render_ng_input(branch_id, year, month, num_days, can_edit)

    with tabs[2]:
        render_prev_history(branch_id, can_edit)


def render_requests_input(branch_id: str, year: int, month: int, num_days: int, can_edit: bool):
    """희망 입력"""
    st.subheader(t("requests.request_input"))

    staff_list = get_staff_for_branch(branch_id)
    if not staff_list:
        st.info(t("common.none"))
        return

    # 현재 희망 데이터
    requests = get_session("requests", {})

    # 시프트 옵션
    day_shifts = get_session("shifts_day", DEFAULT_DAY_SHIFTS)
    night_shifts = get_session("shifts_night", DEFAULT_NIGHT_SHIFTS)
    all_shifts = [""] + day_shifts + night_shifts + [SHIFT_OFF, SHIFT_PUBLIC_OFF]

    # 입력 방식 선택
    input_method = st.radio(
        t("common.select"),
        [t("requests.manual_input"), t("requests.csv_upload")],
        horizontal=True,
        label_visibility="collapsed"
    )

    if input_method == t("requests.csv_upload"):
        render_csv_upload("requests", staff_list, num_days)
    else:
        # 수동 입력
        if can_edit:
            with st.form("request_form"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    staff_name = st.selectbox(
                        t("requests.staff_name"),
                        options=[s.name for s in staff_list]
                    )

                with col2:
                    day = st.selectbox(
                        t("requests.day"),
                        options=list(range(1, num_days + 1))
                    )

                with col3:
                    shift = st.selectbox(
                        t("requests.shift"),
                        options=all_shifts[1:]  # 빈 문자열 제외
                    )

                submitted = st.form_submit_button(t("requests.add_request"))

                if submitted:
                    if staff_name not in requests:
                        requests[staff_name] = {}
                    requests[staff_name][day] = shift
                    set_session("requests", requests)
                    st.success(t("common.success"))
                    st.rerun()

    # 현재 희망 요약
    st.divider()
    st.subheader(t("requests.request_summary"))
    render_requests_summary(requests, staff_list, num_days)


def render_ng_input(branch_id: str, year: int, month: int, num_days: int, can_edit: bool):
    """NG 입력"""
    st.subheader(t("requests.ng_input"))

    staff_list = get_staff_for_branch(branch_id)
    if not staff_list:
        st.info(t("common.none"))
        return

    # 현재 NG 데이터
    ng_shifts = get_session("ng_shifts", {})

    # 시프트 옵션
    day_shifts = get_session("shifts_day", DEFAULT_DAY_SHIFTS)
    night_shifts = get_session("shifts_night", DEFAULT_NIGHT_SHIFTS)
    all_shifts = day_shifts + night_shifts

    # 입력 방식 선택
    input_method = st.radio(
        t("common.select"),
        [t("requests.manual_input"), t("requests.csv_upload")],
        horizontal=True,
        key="ng_input_method",
        label_visibility="collapsed"
    )

    if input_method == t("requests.csv_upload"):
        render_csv_upload("ng_shifts", staff_list, num_days)
    else:
        # 수동 입력
        if can_edit:
            with st.form("ng_form"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    staff_name = st.selectbox(
                        t("requests.staff_name"),
                        options=[s.name for s in staff_list],
                        key="ng_staff"
                    )

                with col2:
                    day = st.selectbox(
                        t("requests.day"),
                        options=list(range(1, num_days + 1)),
                        key="ng_day"
                    )

                with col3:
                    shift = st.multiselect(
                        t("requests.shift"),
                        options=all_shifts,
                        key="ng_shift"
                    )

                submitted = st.form_submit_button(t("requests.add_ng"))

                if submitted and shift:
                    if staff_name not in ng_shifts:
                        ng_shifts[staff_name] = {}
                    if day not in ng_shifts[staff_name]:
                        ng_shifts[staff_name][day] = []
                    ng_shifts[staff_name][day].extend(shift)
                    ng_shifts[staff_name][day] = list(set(ng_shifts[staff_name][day]))
                    set_session("ng_shifts", ng_shifts)
                    st.success(t("common.success"))
                    st.rerun()

    # 현재 NG 요약
    st.divider()
    st.subheader(t("requests.ng_summary"))
    render_ng_summary(ng_shifts, staff_list, num_days)


def render_prev_history(branch_id: str, can_edit: bool):
    """이전 이력 입력"""
    st.subheader(t("schedule.previous_history"))
    st.caption("d-3, d-2, d-1 (전월 마지막 3일)")

    staff_list = get_staff_for_branch(branch_id)
    if not staff_list:
        st.info(t("common.none"))
        return

    prev_history = get_session("prev_history", {})

    # 시프트 옵션
    day_shifts = get_session("shifts_day", DEFAULT_DAY_SHIFTS)
    night_shifts = get_session("shifts_night", DEFAULT_NIGHT_SHIFTS)
    all_shifts = [""] + day_shifts + night_shifts + [SHIFT_OFF]

    if can_edit:
        # 데이터 에디터로 표시
        data = []
        for staff in staff_list:
            history = prev_history.get(staff.name, ["", "", ""])
            while len(history) < 3:
                history.insert(0, "")
            data.append({
                t("staff.name"): staff.name,
                "d-3": history[0] if len(history) > 0 else "",
                "d-2": history[1] if len(history) > 1 else "",
                "d-1": history[2] if len(history) > 2 else "",
            })

        df = pd.DataFrame(data)

        edited_df = st.data_editor(
            df,
            column_config={
                "d-3": st.column_config.SelectboxColumn(options=all_shifts),
                "d-2": st.column_config.SelectboxColumn(options=all_shifts),
                "d-1": st.column_config.SelectboxColumn(options=all_shifts),
            },
            use_container_width=True,
            key="prev_history_editor"
        )

        if st.button(t("common.save"), key="save_prev_history"):
            new_history = {}
            for _, row in edited_df.iterrows():
                name = row[t("staff.name")]
                new_history[name] = [row["d-3"], row["d-2"], row["d-1"]]
            set_session("prev_history", new_history)
            st.success(t("common.success"))
    else:
        # 읽기 전용 표시
        data = []
        for staff in staff_list:
            history = prev_history.get(staff.name, ["", "", ""])
            data.append({
                t("staff.name"): staff.name,
                "d-3": history[0] if len(history) > 0 else "",
                "d-2": history[1] if len(history) > 1 else "",
                "d-1": history[2] if len(history) > 2 else "",
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True)


def render_csv_upload(data_type: str, staff_list: list, num_days: int):
    """CSV 업로드"""
    uploaded = st.file_uploader(
        t("requests.csv_upload"),
        type=["csv"],
        key=f"csv_{data_type}"
    )

    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.dataframe(df, use_container_width=True)

            if st.button(t("common.import"), key=f"import_{data_type}"):
                # CSV 파싱 로직 (형식에 따라 조정 필요)
                st.success(t("common.success"))
        except Exception as e:
            st.error(f"{t('errors.generic')}: {e}")


def render_requests_summary(requests: dict, staff_list: list, num_days: int):
    """희망 요약 테이블"""
    if not requests:
        st.info(t("common.none"))
        return

    # 테이블 생성
    data = []
    for staff in staff_list:
        if staff.name in requests:
            staff_req = requests[staff.name]
            row = {t("staff.name"): staff.name}
            for d in range(1, num_days + 1):
                row[d] = staff_req.get(d, "")
            data.append(row)

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

        if st.button(t("requests.clear_all"), key="clear_requests"):
            set_session("requests", {})
            st.rerun()


def render_ng_summary(ng_shifts: dict, staff_list: list, num_days: int):
    """NG 요약 테이블"""
    if not ng_shifts:
        st.info(t("common.none"))
        return

    # 테이블 생성
    data = []
    for staff in staff_list:
        if staff.name in ng_shifts:
            staff_ng = ng_shifts[staff.name]
            row = {t("staff.name"): staff.name}
            for d in range(1, num_days + 1):
                ng_list = staff_ng.get(d, [])
                row[d] = ",".join(ng_list) if ng_list else ""
            data.append(row)

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

        if st.button(t("requests.clear_all"), key="clear_ng"):
            set_session("ng_shifts", {})
            st.rerun()
