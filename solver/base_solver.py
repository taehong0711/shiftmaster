# solver/base_solver.py
"""솔버 베이스 클래스"""

from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from dataclasses import dataclass, field
from config.constants import (
    SHIFT_OFF, SHIFT_PUBLIC_OFF,
    SOLVER_MAX_TIME_SECONDS, SOLVER_DEFAULT_K_BEST
)


@dataclass
class SolverConfig:
    """솔버 설정"""
    max_time_seconds: int = SOLVER_MAX_TIME_SECONDS
    k_best: int = SOLVER_DEFAULT_K_BEST
    seed: Optional[int] = None
    log_search_progress: bool = False


@dataclass
class StaffInfo:
    """스태프 정보"""
    name: str
    gender: str = "M"
    role: str = "staff"
    target_off: int = 8
    nenkyu: int = 0
    skills: List[str] = field(default_factory=list)
    prefer: str = ""

    def has_skill(self, skill: str) -> bool:
        return skill in self.skills

    def can_night(self) -> bool:
        return "NIGHT" in self.skills

    def can_l1(self) -> bool:
        return "L1" in self.skills


@dataclass
class SolverInput:
    """솔버 입력 데이터"""
    year: int
    month: int
    num_days: int
    staff_list: List[StaffInfo]
    day_shifts: List[str]
    night_shifts: List[str]
    closed_days: List[int] = field(default_factory=list)
    requests: Dict[str, Dict[int, str]] = field(default_factory=dict)  # {staff: {day: shift}}
    ng_shifts: Dict[str, Dict[int, List[str]]] = field(default_factory=dict)  # {staff: {day: [shifts]}}
    prev_history: Dict[str, List[str]] = field(default_factory=dict)  # {staff: [d-3, d-2, d-1]}
    fixed_cells: Dict[str, Dict[int, str]] = field(default_factory=dict)  # Stage2용
    required_shifts: List[str] = field(default_factory=list)  # 매일 최소 1명 필수 시프트


@dataclass
class SolverResult:
    """솔버 결과"""
    success: bool
    df: Optional[pd.DataFrame] = None
    summary_df: Optional[pd.DataFrame] = None
    objective_value: int = 0
    status: str = ""
    message: str = ""


class BaseSolver:
    """솔버 베이스 클래스"""

    def __init__(self, config: SolverConfig = None):
        self.config = config or SolverConfig()
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # 솔버 설정
        self.solver.parameters.max_time_in_seconds = self.config.max_time_seconds
        if self.config.seed is not None:
            self.solver.parameters.random_seed = self.config.seed
        if self.config.log_search_progress:
            self.solver.parameters.log_search_progress = True

        # 변수 저장
        self.shift_vars: Dict[Tuple[int, int, int], Any] = {}  # (staff_idx, day, shift_idx) -> BoolVar
        self.penalty_vars: List[Any] = []

        # 입력 데이터
        self.input: Optional[SolverInput] = None

    def create_shift_variables(self, staff_list: List[StaffInfo], num_days: int,
                               all_shifts: List[str]) -> Dict[Tuple[int, int, int], Any]:
        """시프트 변수 생성"""
        shift_vars = {}
        for s_idx, staff in enumerate(staff_list):
            for d in range(1, num_days + 1):
                for sh_idx, shift in enumerate(all_shifts):
                    var_name = f"shift_s{s_idx}_d{d}_sh{sh_idx}"
                    shift_vars[(s_idx, d, sh_idx)] = self.model.NewBoolVar(var_name)
        return shift_vars

    def add_exactly_one_shift_per_day(self, staff_list: List[StaffInfo], num_days: int,
                                      all_shifts: List[str]):
        """하루에 정확히 하나의 시프트만 할당"""
        for s_idx in range(len(staff_list)):
            for d in range(1, num_days + 1):
                day_vars = [
                    self.shift_vars[(s_idx, d, sh_idx)]
                    for sh_idx in range(len(all_shifts))
                ]
                self.model.AddExactlyOne(day_vars)

    def add_skill_constraints(self, staff_list: List[StaffInfo], num_days: int,
                             all_shifts: List[str], skill_map: Dict[str, str]):
        """스킬 제약 추가"""
        for s_idx, staff in enumerate(staff_list):
            for d in range(1, num_days + 1):
                for sh_idx, shift in enumerate(all_shifts):
                    if shift in skill_map:
                        required_skill = skill_map[shift]
                        if not staff.has_skill(required_skill):
                            # 스킬 없으면 해당 시프트 불가
                            self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 0)

    def add_ng_constraints(self, staff_list: List[StaffInfo], num_days: int,
                          all_shifts: List[str], ng_shifts: Dict[str, Dict[int, List[str]]]):
        """NG 시프트 제약 추가"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}

        for s_idx, staff in enumerate(staff_list):
            staff_ng = ng_shifts.get(staff.name, {})
            for d, ng_list in staff_ng.items():
                if 1 <= d <= num_days:
                    for ng_shift in ng_list:
                        if ng_shift in shift_to_idx:
                            sh_idx = shift_to_idx[ng_shift]
                            self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 0)

    def add_request_soft_constraints(self, staff_list: List[StaffInfo], num_days: int,
                                    all_shifts: List[str], requests: Dict[str, Dict[int, str]],
                                    weight: int = 50000):
        """희망 시프트 소프트 제약 추가"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}

        for s_idx, staff in enumerate(staff_list):
            staff_req = requests.get(staff.name, {})
            for d, req_shift in staff_req.items():
                if 1 <= d <= num_days and req_shift in shift_to_idx:
                    sh_idx = shift_to_idx[req_shift]
                    # 희망 불충족 시 페널티
                    penalty = self.model.NewBoolVar(f"req_penalty_s{s_idx}_d{d}")
                    self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 1).OnlyEnforceIf(penalty.Not())
                    self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 0).OnlyEnforceIf(penalty)
                    self.penalty_vars.append((penalty, weight))

    def add_night_off_constraint(self, staff_list: List[StaffInfo], num_days: int,
                                all_shifts: List[str], night_shifts: List[str]):
        """야간 근무 후 휴무 제약"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_idx = shift_to_idx.get(SHIFT_OFF)

        if off_idx is None:
            return

        night_indices = [shift_to_idx[ns] for ns in night_shifts if ns in shift_to_idx]

        for s_idx in range(len(staff_list)):
            for d in range(1, num_days):  # 마지막 날 제외
                for n_idx in night_indices:
                    # 야간 근무 시 다음 날 반드시 휴무
                    self.model.Add(
                        self.shift_vars[(s_idx, d + 1, off_idx)] == 1
                    ).OnlyEnforceIf(self.shift_vars[(s_idx, d, n_idx)])

    def add_consecutive_work_limit(self, staff_list: List[StaffInfo], num_days: int,
                                   all_shifts: List[str], max_consecutive: int = 5):
        """연속 근무 제한"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_indices = [
            shift_to_idx.get(SHIFT_OFF),
            shift_to_idx.get(SHIFT_PUBLIC_OFF)
        ]
        off_indices = [i for i in off_indices if i is not None]

        for s_idx in range(len(staff_list)):
            for start_d in range(1, num_days - max_consecutive + 1):
                # max_consecutive + 1일 연속 근무 불가
                work_vars = []
                for d in range(start_d, start_d + max_consecutive + 1):
                    if d <= num_days:
                        # 해당 날 근무 여부 (휴무가 아니면 근무)
                        is_working = self.model.NewBoolVar(f"work_s{s_idx}_d{d}")
                        off_vars = [self.shift_vars[(s_idx, d, off_i)] for off_i in off_indices]
                        if off_vars:
                            # 모든 휴무 시프트가 0이면 근무
                            self.model.Add(sum(off_vars) == 0).OnlyEnforceIf(is_working)
                            self.model.Add(sum(off_vars) >= 1).OnlyEnforceIf(is_working.Not())
                        work_vars.append(is_working)

                if len(work_vars) == max_consecutive + 1:
                    # 연속 근무 일수 제한
                    self.model.Add(sum(work_vars) <= max_consecutive)

    def add_target_off_soft_constraint(self, staff_list: List[StaffInfo], num_days: int,
                                       all_shifts: List[str], weight: int = 30000):
        """목표 휴일 수 소프트 제약"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_indices = [
            shift_to_idx.get(SHIFT_OFF),
            shift_to_idx.get(SHIFT_PUBLIC_OFF)
        ]
        off_indices = [i for i in off_indices if i is not None]

        for s_idx, staff in enumerate(staff_list):
            target = staff.target_off
            off_count = sum(
                self.shift_vars[(s_idx, d, off_i)]
                for d in range(1, num_days + 1)
                for off_i in off_indices
            )

            # 편차에 대한 페널티
            deviation = self.model.NewIntVar(0, num_days, f"off_dev_s{s_idx}")
            self.model.AddAbsEquality(deviation, off_count - target)
            self.penalty_vars.append((deviation, weight))

    def set_objective(self):
        """목적 함수 설정 (페널티 최소화)"""
        if not self.penalty_vars:
            return

        total_penalty = sum(
            var * weight if isinstance(var, int) else var * weight
            for var, weight in self.penalty_vars
        )
        self.model.Minimize(total_penalty)

    def solve(self) -> SolverResult:
        """솔버 실행"""
        status = self.solver.Solve(self.model)

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return SolverResult(
                success=True,
                objective_value=int(self.solver.ObjectiveValue()),
                status=status_map.get(status, "UNKNOWN"),
                message="Solution found"
            )
        else:
            return SolverResult(
                success=False,
                status=status_map.get(status, "UNKNOWN"),
                message="No solution found"
            )

    def get_solution_value(self, var) -> int:
        """변수 값 가져오기"""
        return self.solver.Value(var)

    def add_nogood_cut(self, all_shifts: List[str], staff_list: List[StaffInfo], num_days: int):
        """현재 솔루션 제외 (다음 솔루션 찾기용)"""
        solution_literals = []
        for s_idx in range(len(staff_list)):
            for d in range(1, num_days + 1):
                for sh_idx in range(len(all_shifts)):
                    var = self.shift_vars[(s_idx, d, sh_idx)]
                    if self.solver.Value(var) == 1:
                        solution_literals.append(var)
                    else:
                        solution_literals.append(var.Not())

        # 현재 솔루션과 다른 솔루션 찾기
        self.model.AddBoolOr([lit.Not() for lit in solution_literals])

    def extract_schedule_df(self, staff_list: List[StaffInfo], num_days: int,
                           all_shifts: List[str]) -> pd.DataFrame:
        """솔루션에서 스케줄 DataFrame 추출"""
        data = []
        for s_idx, staff in enumerate(staff_list):
            row = {"name": staff.name}
            off_count = 0
            work_count = 0

            for d in range(1, num_days + 1):
                assigned_shift = ""
                for sh_idx, shift in enumerate(all_shifts):
                    if self.solver.Value(self.shift_vars[(s_idx, d, sh_idx)]) == 1:
                        assigned_shift = shift
                        break

                row[d] = assigned_shift

                if assigned_shift in [SHIFT_OFF, SHIFT_PUBLIC_OFF]:
                    off_count += 1
                elif assigned_shift:
                    work_count += 1

            row["休日数"] = off_count
            row["勤務数"] = work_count
            data.append(row)

        return pd.DataFrame(data)

    def build_summary_df(self, schedule_df: pd.DataFrame, num_days: int,
                        day_shifts: List[str], night_shifts: List[str]) -> pd.DataFrame:
        """일별 요약 DataFrame 생성"""
        all_shifts = day_shifts + night_shifts + [SHIFT_OFF, SHIFT_PUBLIC_OFF]
        summary_data = []

        for d in range(1, num_days + 1):
            day_data = {"日": d}
            col = schedule_df[d] if d in schedule_df.columns else pd.Series()

            for shift in all_shifts:
                count = (col == shift).sum() if len(col) > 0 else 0
                day_data[shift] = count

            # 근무자 수 (휴무 제외)
            work_count = len(col) - (col == SHIFT_OFF).sum() - (col == SHIFT_PUBLIC_OFF).sum()
            day_data["勤務"] = work_count

            summary_data.append(day_data)

        return pd.DataFrame(summary_data)
