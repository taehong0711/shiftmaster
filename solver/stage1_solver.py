# solver/stage1_solver.py
"""Stage1 솔버 - 야간 시프트 + L1 배치"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from ortools.sat.python import cp_model

from solver.base_solver import BaseSolver, SolverConfig, SolverInput, SolverResult, StaffInfo
from solver.constraint_builder import ConstraintBuilder
from models.constraint import Constraint
from config.constants import SHIFT_OFF, SHIFT_PUBLIC_OFF


class Stage1Solver(BaseSolver):
    """Stage1 솔버: 야간 시프트 + L1 배치"""

    def __init__(self, config: SolverConfig = None):
        super().__init__(config)
        self.stage1_shifts: List[str] = []  # 야간 + L1 + 휴무

    def setup(self, solver_input: SolverInput, constraints: List[Constraint] = None):
        """솔버 설정"""
        self.input = solver_input

        # Stage1에서 다루는 시프트: 야간 + L1 + 휴무
        self.stage1_shifts = solver_input.night_shifts + ["L1", SHIFT_OFF, SHIFT_PUBLIC_OFF]

        # 시프트 변수 생성
        self.shift_vars = self.create_shift_variables(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts
        )

        # 기본 제약: 하루에 하나의 시프트
        self.add_exactly_one_shift_per_day(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts
        )

        # 스킬 제약
        skill_map = {
            "L1": "L1",
        }
        for ns in solver_input.night_shifts:
            skill_map[ns] = "NIGHT"

        self.add_skill_constraints(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts,
            skill_map
        )

        # NG 제약
        self.add_ng_constraints(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts,
            solver_input.ng_shifts
        )

        # 야간 후 휴무 제약
        self.add_night_off_constraint(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts,
            solver_input.night_shifts
        )

        # 이전 이력 기반 제약 (d-1, d-2, d-3)
        self._add_prev_history_constraints(solver_input)

        # 연속 근무 제한
        self.add_consecutive_work_limit(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts,
            max_consecutive=5
        )

        # 희망 소프트 제약
        self.add_request_soft_constraints(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts,
            solver_input.requests,
            weight=50000
        )

        # 목표 휴일 소프트 제약
        self.add_target_off_soft_constraint(
            solver_input.staff_list,
            solver_input.num_days,
            self.stage1_shifts,
            weight=30000
        )

        # L1 일별 배치 (매일 1명)
        self._add_l1_daily_constraint(solver_input)

        # 야간 시프트 균형
        self._add_night_balance_constraint(solver_input)

        # 동적 제약 적용
        if constraints:
            builder = ConstraintBuilder(self)
            builder.build_constraints(
                constraints,
                solver_input.staff_list,
                solver_input.num_days,
                self.stage1_shifts,
                solver_input.night_shifts
            )

        # 목적 함수 설정
        self.set_objective()

    def _add_prev_history_constraints(self, solver_input: SolverInput):
        """이전 이력 기반 제약"""
        shift_to_idx = {s: i for i, s in enumerate(self.stage1_shifts)}
        off_idx = shift_to_idx.get(SHIFT_OFF)
        night_indices = [shift_to_idx[ns] for ns in solver_input.night_shifts if ns in shift_to_idx]

        for s_idx, staff in enumerate(solver_input.staff_list):
            history = solver_input.prev_history.get(staff.name, [])
            if not history or len(history) < 1:
                continue

            # d-1이 야간이면 d=1은 휴무
            d_minus_1 = history[-1] if len(history) >= 1 else ""
            if d_minus_1 in solver_input.night_shifts and off_idx is not None:
                self.model.Add(self.shift_vars[(s_idx, 1, off_idx)] == 1)

            # d-2, d-3도 고려하여 연속 근무 체크
            if len(history) >= 3:
                # 이미 4일 연속 근무인 경우 d=1은 휴무
                consecutive_work = 0
                for h in history:
                    if h not in [SHIFT_OFF, SHIFT_PUBLIC_OFF, "", "-"]:
                        consecutive_work += 1
                    else:
                        consecutive_work = 0

                if consecutive_work >= 5 and off_idx is not None:
                    self.model.Add(self.shift_vars[(s_idx, 1, off_idx)] == 1)

    def _add_l1_daily_constraint(self, solver_input: SolverInput):
        """매일 L1 1명 배치"""
        shift_to_idx = {s: i for i, s in enumerate(self.stage1_shifts)}
        l1_idx = shift_to_idx.get("L1")

        if l1_idx is None:
            return

        for d in range(1, solver_input.num_days + 1):
            # 휴관일이 아닌 경우만
            if d not in solver_input.closed_days:
                l1_count = sum(
                    self.shift_vars[(s_idx, d, l1_idx)]
                    for s_idx in range(len(solver_input.staff_list))
                )
                # 정확히 1명 (소프트 제약으로 처리)
                deviation = self.model.NewIntVar(0, len(solver_input.staff_list), f"l1_dev_d{d}")
                self.model.AddAbsEquality(deviation, l1_count - 1)
                self.penalty_vars.append((deviation, 35000))

    def _add_night_balance_constraint(self, solver_input: SolverInput):
        """야간 시프트 균형 배분"""
        shift_to_idx = {s: i for i, s in enumerate(self.stage1_shifts)}
        night_indices = [shift_to_idx[ns] for ns in solver_input.night_shifts if ns in shift_to_idx]

        if not night_indices:
            return

        # 야간 가능 스태프
        night_staff = [(s_idx, staff) for s_idx, staff in enumerate(solver_input.staff_list)
                      if staff.can_night()]

        if len(night_staff) < 2:
            return

        # 각 스태프의 야간 횟수
        night_counts = []
        for s_idx, staff in night_staff:
            count = sum(
                self.shift_vars[(s_idx, d, n_idx)]
                for d in range(1, solver_input.num_days + 1)
                for n_idx in night_indices
            )
            night_counts.append((s_idx, count))

        # 균형 페널티
        total = sum(c for _, c in night_counts)
        for s_idx, count in night_counts:
            deviation = self.model.NewIntVar(0, solver_input.num_days, f"night_balance_s{s_idx}")
            self.model.AddAbsEquality(deviation, count * len(night_staff) - total)
            self.penalty_vars.append((deviation, 20000 // len(night_staff)))

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
                    self.stage1_shifts
                )
                result.summary_df = self.build_summary_df(
                    result.df,
                    self.input.num_days,
                    ["L1"],  # Stage1에서는 L1만 day shift
                    self.input.night_shifts
                )
                results.append(result)

                # 다음 솔루션을 위해 현재 솔루션 제외
                if i < k - 1:
                    self.add_nogood_cut(
                        self.stage1_shifts,
                        self.input.staff_list,
                        self.input.num_days
                    )
            else:
                # 더 이상 솔루션 없음
                break

        return results


def solve_stage1(solver_input: SolverInput, constraints: List[Constraint] = None,
                config: SolverConfig = None) -> SolverResult:
    """Stage1 단일 솔루션"""
    solver = Stage1Solver(config)
    solver.setup(solver_input, constraints)
    result = solver.solve()

    if result.success:
        result.df = solver.extract_schedule_df(
            solver_input.staff_list,
            solver_input.num_days,
            solver.stage1_shifts
        )
        result.summary_df = solver.build_summary_df(
            result.df,
            solver_input.num_days,
            ["L1"],
            solver_input.night_shifts
        )

    return result


def solve_stage1_multi(solver_input: SolverInput, constraints: List[Constraint] = None,
                      config: SolverConfig = None, k: int = 3) -> List[SolverResult]:
    """Stage1 다중 솔루션"""
    solver = Stage1Solver(config)
    solver.setup(solver_input, constraints)
    return solver.solve_multi(k)
