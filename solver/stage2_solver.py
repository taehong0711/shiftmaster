# solver/stage2_solver.py
"""Stage2 솔버 - 주간 시프트 배치"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from ortools.sat.python import cp_model

from solver.base_solver import BaseSolver, SolverConfig, SolverInput, SolverResult, StaffInfo
from solver.constraint_builder import ConstraintBuilder
from models.constraint import Constraint
from config.constants import SHIFT_OFF, SHIFT_PUBLIC_OFF


class Stage2Solver(BaseSolver):
    """Stage2 솔버: Stage1 결과를 고정하고 주간 시프트 배치"""

    def __init__(self, config: SolverConfig = None):
        super().__init__(config)
        self.all_shifts: List[str] = []

    def setup(self, solver_input: SolverInput, stage1_df: pd.DataFrame,
             constraints: List[Constraint] = None):
        """솔버 설정"""
        self.input = solver_input

        # 모든 시프트 (주간 + 야간 + 휴무)
        self.all_shifts = (
            solver_input.day_shifts +
            solver_input.night_shifts +
            [SHIFT_OFF, SHIFT_PUBLIC_OFF]
        )

        # 시프트 변수 생성
        self.shift_vars = self.create_shift_variables(
            solver_input.staff_list,
            solver_input.num_days,
            self.all_shifts
        )

        shift_to_idx = {s: i for i, s in enumerate(self.all_shifts)}

        # Stage1 결과 고정
        self._fix_stage1_cells(solver_input, stage1_df, shift_to_idx)

        # 수동 편집 셀 고정
        self._fix_edited_cells(solver_input, shift_to_idx)

        # 기본 제약: 하루에 하나의 시프트
        self.add_exactly_one_shift_per_day(
            solver_input.staff_list,
            solver_input.num_days,
            self.all_shifts
        )

        # 스킬 제약 (주간 시프트는 일반적으로 스킬 제한 없음)
        skill_map = {"L1": "L1"}
        for ns in solver_input.night_shifts:
            skill_map[ns] = "NIGHT"

        self.add_skill_constraints(
            solver_input.staff_list,
            solver_input.num_days,
            self.all_shifts,
            skill_map
        )

        # NG 제약
        self.add_ng_constraints(
            solver_input.staff_list,
            solver_input.num_days,
            self.all_shifts,
            solver_input.ng_shifts
        )

        # 연속 근무 제한
        self.add_consecutive_work_limit(
            solver_input.staff_list,
            solver_input.num_days,
            self.all_shifts,
            max_consecutive=5
        )

        # 희망 소프트 제약 (주간 시프트용)
        self._add_day_shift_request_constraints(solver_input, shift_to_idx)

        # 주간 시프트 균형
        self._add_day_shift_balance(solver_input, shift_to_idx)

        # 일별 커버리지
        self._add_daily_coverage(solver_input, shift_to_idx)

        # 동적 제약 적용
        if constraints:
            builder = ConstraintBuilder(self)
            builder.build_constraints(
                constraints,
                solver_input.staff_list,
                solver_input.num_days,
                self.all_shifts,
                solver_input.night_shifts
            )

        # 목적 함수 설정
        self.set_objective()

    def _fix_stage1_cells(self, solver_input: SolverInput, stage1_df: pd.DataFrame,
                         shift_to_idx: Dict[str, int]):
        """Stage1 결과 고정"""
        name_to_idx = {staff.name: idx for idx, staff in enumerate(solver_input.staff_list)}

        for _, row in stage1_df.iterrows():
            staff_name = row.get("name", "")
            if staff_name not in name_to_idx:
                continue

            s_idx = name_to_idx[staff_name]

            for d in range(1, solver_input.num_days + 1):
                if d in row.index or str(d) in row.index:
                    shift = row.get(d, row.get(str(d), ""))
                    if shift and shift in shift_to_idx:
                        # Stage1에서 할당된 시프트 고정 (야간, L1, 휴무)
                        if shift in solver_input.night_shifts or shift in ["L1", SHIFT_OFF, SHIFT_PUBLIC_OFF]:
                            sh_idx = shift_to_idx[shift]
                            self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 1)

    def _fix_edited_cells(self, solver_input: SolverInput, shift_to_idx: Dict[str, int]):
        """수동 편집 셀 고정"""
        name_to_idx = {staff.name: idx for idx, staff in enumerate(solver_input.staff_list)}

        for staff_name, day_shifts in solver_input.fixed_cells.items():
            if staff_name not in name_to_idx:
                continue

            s_idx = name_to_idx[staff_name]

            for d, shift in day_shifts.items():
                d = int(d)
                if 1 <= d <= solver_input.num_days and shift in shift_to_idx:
                    sh_idx = shift_to_idx[shift]
                    self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 1)

    def _add_day_shift_request_constraints(self, solver_input: SolverInput,
                                           shift_to_idx: Dict[str, int]):
        """주간 시프트 희망 제약"""
        for s_idx, staff in enumerate(solver_input.staff_list):
            staff_req = solver_input.requests.get(staff.name, {})
            for d, req_shift in staff_req.items():
                d = int(d) if isinstance(d, str) else d
                if 1 <= d <= solver_input.num_days:
                    # 주간 시프트 희망만 처리 (야간/L1/휴무는 Stage1에서 처리됨)
                    if req_shift in solver_input.day_shifts and req_shift in shift_to_idx:
                        sh_idx = shift_to_idx[req_shift]
                        penalty = self.model.NewBoolVar(f"day_req_penalty_s{s_idx}_d{d}")
                        self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 1).OnlyEnforceIf(penalty.Not())
                        self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 0).OnlyEnforceIf(penalty)
                        self.penalty_vars.append((penalty, 40000))

    def _add_day_shift_balance(self, solver_input: SolverInput, shift_to_idx: Dict[str, int]):
        """주간 시프트 균형"""
        day_shift_indices = [shift_to_idx[ds] for ds in solver_input.day_shifts if ds in shift_to_idx]

        if not day_shift_indices:
            return

        # 각 스태프의 주간 시프트 횟수
        day_shift_counts = []
        for s_idx in range(len(solver_input.staff_list)):
            count = sum(
                self.shift_vars[(s_idx, d, ds_idx)]
                for d in range(1, solver_input.num_days + 1)
                for ds_idx in day_shift_indices
            )
            day_shift_counts.append(count)

        # 균형 페널티
        total = sum(day_shift_counts)
        n_staff = len(solver_input.staff_list)

        for s_idx, count in enumerate(day_shift_counts):
            deviation = self.model.NewIntVar(0, solver_input.num_days, f"day_balance_s{s_idx}")
            self.model.AddAbsEquality(deviation, count * n_staff - total)
            self.penalty_vars.append((deviation, 10000 // n_staff))

    def _add_daily_coverage(self, solver_input: SolverInput, shift_to_idx: Dict[str, int]):
        """일별 커버리지 제약"""
        off_indices = [
            shift_to_idx.get(SHIFT_OFF),
            shift_to_idx.get(SHIFT_PUBLIC_OFF)
        ]
        off_indices = [i for i in off_indices if i is not None]

        min_coverage = 3  # 최소 근무자 수

        for d in range(1, solver_input.num_days + 1):
            if d in solver_input.closed_days:
                continue

            working_count = 0
            for s_idx in range(len(solver_input.staff_list)):
                is_working = self.model.NewBoolVar(f"working_s{s_idx}_d{d}")
                off_vars = [self.shift_vars[(s_idx, d, off_i)] for off_i in off_indices]
                if off_vars:
                    self.model.Add(sum(off_vars) == 0).OnlyEnforceIf(is_working)
                    self.model.Add(sum(off_vars) >= 1).OnlyEnforceIf(is_working.Not())
                    working_count += is_working

            # 소프트 제약으로 처리
            shortage = self.model.NewIntVar(0, len(solver_input.staff_list), f"coverage_shortage_d{d}")
            self.model.Add(shortage >= min_coverage - working_count)
            self.model.Add(shortage >= 0)
            self.penalty_vars.append((shortage, 25000))

    def solve_multi(self, k: int = 3) -> List[SolverResult]:
        """k개의 솔루션 찾기"""
        results = []

        for i in range(k):
            result = self.solve()

            if result.success:
                # 스케줄 추출
                result.df = self.extract_schedule_df(
                    self.input.staff_list,
                    self.input.num_days,
                    self.all_shifts
                )
                result.summary_df = self.build_summary_df(
                    result.df,
                    self.input.num_days,
                    self.input.day_shifts,
                    self.input.night_shifts
                )
                results.append(result)

                # 다음 솔루션을 위해 현재 솔루션 제외
                if i < k - 1:
                    self.add_nogood_cut(
                        self.all_shifts,
                        self.input.staff_list,
                        self.input.num_days
                    )
            else:
                break

        return results


def solve_stage2(solver_input: SolverInput, stage1_df: pd.DataFrame,
                constraints: List[Constraint] = None,
                config: SolverConfig = None) -> SolverResult:
    """Stage2 단일 솔루션"""
    solver = Stage2Solver(config)
    solver.setup(solver_input, stage1_df, constraints)
    result = solver.solve()

    if result.success:
        result.df = solver.extract_schedule_df(
            solver_input.staff_list,
            solver_input.num_days,
            solver.all_shifts
        )
        result.summary_df = solver.build_summary_df(
            result.df,
            solver_input.num_days,
            solver_input.day_shifts,
            solver_input.night_shifts
        )

    return result


def solve_stage2_multi(solver_input: SolverInput, stage1_df: pd.DataFrame,
                      constraints: List[Constraint] = None,
                      config: SolverConfig = None, k: int = 3) -> List[SolverResult]:
    """Stage2 다중 솔루션"""
    solver = Stage2Solver(config)
    solver.setup(solver_input, stage1_df, constraints)
    return solver.solve_multi(k)
