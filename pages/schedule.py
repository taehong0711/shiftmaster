# pages/schedule.py
"""시프트 생성 페이지"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from calendar import monthrange
from io import BytesIO

from localization import t
from core.session import get_current_branch_id, get_session, set_session
from core.auth import get_current_user, is_editor
from models.staff import get_staff_for_branch, Staff
from models.constraint import get_enabled_constraints
from services.shift_service import ShiftService
from services.constraint_service import ConstraintService
from solver import (
    SolverConfig, SolverInput, StaffInfo,
    solve_stage1_multi, solve_stage2_multi
)
from config.constants import (
    DEFAULT_DAY_SHIFTS, DEFAULT_NIGHT_SHIFTS,
    SHIFT_OFF, SHIFT_PUBLIC_OFF, SHIFT_COLORS
)


def render():
    """시프트 생성 페이지 렌더링"""
    st.title(t("schedule.title"))

    branch_id = get_current_branch_id()
    if not branch_id:
        st.warning(t("branches.no_branches"))
        return

    # 설정 영역
    with st.expander(t("schedule.settings"), expanded=True):
        render_settings(branch_id)

    st.divider()

    # Stage1
    st.subheader(t("schedule.stage1"))
    render_stage1(branch_id)

    st.divider()

    # Stage2
    st.subheader(t("schedule.stage2"))
    render_stage2(branch_id)

    st.divider()

    # 결과 표시 및 저장
    render_result(branch_id)


def render_settings(branch_id: str):
    """설정 영역 렌더링"""
    col1, col2 = st.columns(2)

    with col1:
        # 대상 월
        today = date.today()
        next_month = date(today.year + (today.month // 12), (today.month % 12) + 1, 1)
        target_date = st.date_input(
            t("schedule.target_month"),
            value=next_month,
            key="target_month"
        )
        set_session("target_year", target_date.year)
        set_session("target_month_num", target_date.month)

    with col2:
        # 후보 수
        k_best = st.slider(t("schedule.k_best"), 1, 8, 3, key="k_best")
        set_session("k_best", k_best)

    # 휴관일
    year = get_session("target_year", today.year)
    month = get_session("target_month_num", today.month)
    num_days = monthrange(year, month)[1]

    closed_days = st.multiselect(
        t("schedule.closed_days"),
        options=list(range(1, num_days + 1)),
        default=get_session("closed_days", []),
        key="closed_days_select"
    )
    set_session("closed_days", closed_days)


def render_stage1(branch_id: str):
    """Stage1 렌더링"""
    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button(t("schedule.generate"), key="gen_stage1", use_container_width=True):
            run_stage1(branch_id)

    # 결과 표시
    stage1_results = get_session("stage1_results")
    if stage1_results:
        st.success(f"{len(stage1_results)} {t('schedule.solution_n', n='')}")

        # 솔루션 선택
        options = [f"{t('schedule.solution_n', n=i+1)} (obj: {r.objective_value})"
                  for i, r in enumerate(stage1_results)]
        selected = st.selectbox(
            t("schedule.select_solution"),
            options=options,
            key="stage1_select"
        )
        selected_idx = options.index(selected) if selected in options else 0
        set_session("selected_stage1_idx", selected_idx)

        # 선택된 결과 표시
        result = stage1_results[selected_idx]
        if result.df is not None:
            st.dataframe(
                style_shift_df(result.df),
                use_container_width=True,
                height=400
            )


def render_stage2(branch_id: str):
    """Stage2 렌더링"""
    stage1_results = get_session("stage1_results")
    if not stage1_results:
        st.info(t("schedule.stage1") + " " + t("common.loading"))
        return

    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button(t("schedule.generate"), key="gen_stage2", use_container_width=True):
            run_stage2(branch_id)

    # 결과 표시
    stage2_results = get_session("stage2_results")
    if stage2_results:
        st.success(f"{len(stage2_results)} {t('schedule.solution_n', n='')}")

        # 솔루션 선택
        options = [f"{t('schedule.solution_n', n=i+1)} (obj: {r.objective_value})"
                  for i, r in enumerate(stage2_results)]
        selected = st.selectbox(
            t("schedule.select_solution"),
            options=options,
            key="stage2_select"
        )
        selected_idx = options.index(selected) if selected in options else 0
        set_session("selected_stage2_idx", selected_idx)

        # 선택된 결과 표시
        result = stage2_results[selected_idx]
        if result.df is not None:
            st.dataframe(
                style_shift_df(result.df),
                use_container_width=True,
                height=400
            )

            # 요약
            if result.summary_df is not None:
                with st.expander(t("schedule.summary")):
                    st.dataframe(result.summary_df, use_container_width=True)


def render_result(branch_id: str):
    """결과 및 저장 영역"""
    stage2_results = get_session("stage2_results")
    if not stage2_results:
        return

    st.subheader(t("schedule.result"))

    selected_idx = get_session("selected_stage2_idx", 0)
    result = stage2_results[selected_idx]

    if result.df is None:
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(t("schedule.save_to_db"), use_container_width=True):
            save_to_db(branch_id, result.df, result.summary_df)

    with col2:
        if st.button(t("schedule.export_excel"), use_container_width=True):
            export_excel(result.df)

    with col3:
        # 저장된 월 로드
        render_load_saved(branch_id)


def run_stage1(branch_id: str):
    """Stage1 솔버 실행"""
    with st.spinner(t("schedule.generating")):
        # 입력 데이터 준비
        solver_input = prepare_solver_input(branch_id)
        if solver_input is None:
            return

        # 제약 조건
        constraints = list(get_enabled_constraints(branch_id))

        # 설정
        config = SolverConfig(
            max_time_seconds=60,
            k_best=get_session("k_best", 3)
        )

        # 솔버 실행
        results = solve_stage1_multi(solver_input, constraints, config, config.k_best)

        if results:
            set_session("stage1_results", results)
            set_session("stage2_results", None)  # Stage2 초기화
            st.success(t("common.success"))
        else:
            st.error(t("schedule.no_solution"))


def run_stage2(branch_id: str):
    """Stage2 솔버 실행"""
    stage1_results = get_session("stage1_results")
    if not stage1_results:
        st.warning(t("schedule.stage1") + " " + t("common.loading"))
        return

    with st.spinner(t("schedule.generating")):
        # Stage1 결과
        selected_idx = get_session("selected_stage1_idx", 0)
        stage1_df = stage1_results[selected_idx].df

        # 입력 데이터 준비
        solver_input = prepare_solver_input(branch_id)
        if solver_input is None:
            return

        # 제약 조건
        constraints = list(get_enabled_constraints(branch_id))

        # 설정
        config = SolverConfig(
            max_time_seconds=60,
            k_best=get_session("k_best", 3)
        )

        # 솔버 실행
        results = solve_stage2_multi(solver_input, stage1_df, constraints, config, config.k_best)

        if results:
            set_session("stage2_results", results)
            st.success(t("common.success"))
        else:
            st.error(t("schedule.no_solution"))


def prepare_solver_input(branch_id: str) -> SolverInput:
    """솔버 입력 데이터 준비"""
    # 스태프 로드
    staff_list = get_staff_for_branch(branch_id)
    if not staff_list:
        st.error(t("errors.not_found"))
        return None

    # 날짜 정보
    year = get_session("target_year", date.today().year)
    month = get_session("target_month_num", date.today().month)
    num_days = monthrange(year, month)[1]

    # StaffInfo 변환
    staff_info_list = [
        StaffInfo(
            name=s.name,
            gender=s.gender,
            role=s.role,
            target_off=s.target_off,
            nenkyu=s.nenkyu,
            skills=s.skills,
            prefer=s.prefer
        )
        for s in staff_list
    ]

    # 시프트 코드
    day_shifts = get_session("shifts_day", DEFAULT_DAY_SHIFTS)
    night_shifts = get_session("shifts_night", DEFAULT_NIGHT_SHIFTS)

    return SolverInput(
        year=year,
        month=month,
        num_days=num_days,
        staff_list=staff_info_list,
        day_shifts=day_shifts,
        night_shifts=night_shifts,
        closed_days=get_session("closed_days", []),
        requests=get_session("requests", {}),
        ng_shifts=get_session("ng_shifts", {}),
        prev_history=get_session("prev_history", {}),
        fixed_cells=get_session("edited_cells", {})
    )


def style_shift_df(df: pd.DataFrame) -> pd.DataFrame:
    """시프트 DataFrame 스타일링"""
    # 간단한 스타일 적용 (Streamlit에서는 제한적)
    return df


def save_to_db(branch_id: str, df: pd.DataFrame, summary_df: pd.DataFrame):
    """DB에 저장"""
    year = get_session("target_year")
    month = get_session("target_month_num")

    summary_data = summary_df.to_dict('records') if summary_df is not None else {}

    success = ShiftService.save_monthly_shifts(branch_id, year, month, df, summary_data)
    if success:
        st.success(t("common.success"))
    else:
        st.error(t("errors.save_failed"))


def export_excel(df: pd.DataFrame):
    """Excel 내보내기"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Shift')
    output.seek(0)

    year = get_session("target_year")
    month = get_session("target_month_num")
    filename = f"shift_{year}_{month:02d}.xlsx"

    st.download_button(
        label=t("schedule.export_excel"),
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def render_load_saved(branch_id: str):
    """저장된 월 로드"""
    saved_months = ShiftService.get_saved_months(branch_id)
    if not saved_months:
        st.info(t("common.none"))
        return

    options = [f"{y}年{m:02d}月" for y, m in saved_months]
    selected = st.selectbox(t("schedule.load_from_db"), options=options, key="load_month")

    if st.button(t("common.select"), key="load_btn"):
        idx = options.index(selected)
        year, month = saved_months[idx]
        shifts = ShiftService.get_monthly_shifts(branch_id, year, month)
        if shifts:
            st.success(f"{len(shifts)} {t('staff.title')}")
