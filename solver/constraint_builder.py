# solver/constraint_builder.py
"""동적 제약 빌더"""

from ortools.sat.python import cp_model
from typing import List, Dict, Any, Tuple, Optional
from models.constraint import Constraint
from solver.base_solver import BaseSolver, StaffInfo
from config.constants import SHIFT_OFF, SHIFT_PUBLIC_OFF


class ConstraintBuilder:
    """JSON 제약 정의를 CP-SAT 제약으로 변환"""

    def __init__(self, solver: BaseSolver):
        self.solver = solver
        self.model = solver.model
        self.shift_vars = solver.shift_vars

    def build_constraints(self, constraints: List[Constraint],
                         staff_list: List[StaffInfo], num_days: int,
                         all_shifts: List[str], night_shifts: List[str]):
        """제약 조건 리스트를 모델에 적용"""
        for constraint in constraints:
            if not constraint.is_enabled:
                continue

            rule_type = constraint.get_rule_type()
            rule = constraint.get_rule()
            weight = constraint.penalty_weight if constraint.is_soft() else None

            try:
                if rule_type == "sequence":
                    self._build_sequence_constraint(constraint, staff_list, num_days, all_shifts, night_shifts)
                elif rule_type == "rolling_window":
                    self._build_rolling_window_constraint(constraint, staff_list, num_days, all_shifts)
                elif rule_type == "basic":
                    self._build_basic_constraint(constraint, staff_list, num_days, all_shifts)
                elif rule_type == "skill_match":
                    self._build_skill_constraint(constraint, staff_list, num_days, all_shifts)
                elif rule_type == "forbidden":
                    self._build_forbidden_constraint(constraint, staff_list, num_days, all_shifts)
                elif rule_type == "preference":
                    self._build_preference_constraint(constraint, staff_list, num_days, all_shifts, weight)
                elif rule_type == "balance":
                    self._build_balance_constraint(constraint, staff_list, num_days, all_shifts, weight)
                elif rule_type == "coverage":
                    self._build_coverage_constraint(constraint, staff_list, num_days, all_shifts, night_shifts, weight)
            except Exception as e:
                print(f"제약 빌드 오류 ({constraint.code}): {e}")

    def _build_sequence_constraint(self, constraint: Constraint,
                                   staff_list: List[StaffInfo], num_days: int,
                                   all_shifts: List[str], night_shifts: List[str]):
        """시퀀스 제약 (예: 야간 후 휴무)"""
        rule = constraint.get_rule()
        after_shifts = rule.get("after_shifts", night_shifts)
        next_day_must_be = rule.get("next_day_must_be", [SHIFT_OFF])

        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        after_indices = [shift_to_idx[s] for s in after_shifts if s in shift_to_idx]
        must_indices = [shift_to_idx[s] for s in next_day_must_be if s in shift_to_idx]

        if not after_indices or not must_indices:
            return

        for s_idx in range(len(staff_list)):
            for d in range(1, num_days):  # 마지막 날 제외
                for a_idx in after_indices:
                    # after_shift 할당 시 다음 날 must_be 중 하나 필수
                    must_vars = [self.shift_vars[(s_idx, d + 1, m_idx)] for m_idx in must_indices]
                    self.model.Add(sum(must_vars) >= 1).OnlyEnforceIf(
                        self.shift_vars[(s_idx, d, a_idx)]
                    )

    def _build_rolling_window_constraint(self, constraint: Constraint,
                                        staff_list: List[StaffInfo], num_days: int,
                                        all_shifts: List[str]):
        """롤링 윈도우 제약 (예: 연속 근무 최대 N일)"""
        rule = constraint.get_rule()
        max_consecutive = rule.get("max_consecutive_work_days", 5)

        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_indices = [shift_to_idx.get(SHIFT_OFF), shift_to_idx.get(SHIFT_PUBLIC_OFF)]
        off_indices = [i for i in off_indices if i is not None]

        for s_idx in range(len(staff_list)):
            for start_d in range(1, num_days - max_consecutive + 1):
                window_days = list(range(start_d, min(start_d + max_consecutive + 1, num_days + 1)))

                if len(window_days) <= max_consecutive:
                    continue

                # 각 날의 근무 여부 변수
                work_vars = []
                for d in window_days:
                    is_working = self.model.NewBoolVar(f"work_{constraint.code}_s{s_idx}_d{d}")
                    off_vars = [self.shift_vars[(s_idx, d, off_i)] for off_i in off_indices]
                    if off_vars:
                        self.model.Add(sum(off_vars) == 0).OnlyEnforceIf(is_working)
                        self.model.Add(sum(off_vars) >= 1).OnlyEnforceIf(is_working.Not())
                    work_vars.append(is_working)

                # 연속 근무 제한
                self.model.Add(sum(work_vars) <= max_consecutive)

    def _build_basic_constraint(self, constraint: Constraint,
                               staff_list: List[StaffInfo], num_days: int,
                               all_shifts: List[str]):
        """기본 제약 (예: 하루 1시프트)"""
        rule = constraint.get_rule()

        if rule.get("exactly_one_shift_per_day"):
            for s_idx in range(len(staff_list)):
                for d in range(1, num_days + 1):
                    day_vars = [self.shift_vars[(s_idx, d, sh_idx)]
                               for sh_idx in range(len(all_shifts))]
                    self.model.AddExactlyOne(day_vars)

    def _build_skill_constraint(self, constraint: Constraint,
                               staff_list: List[StaffInfo], num_days: int,
                               all_shifts: List[str]):
        """스킬 제약"""
        rule = constraint.get_rule()
        skill_map = rule.get("shift_skill_map", {})

        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}

        for s_idx, staff in enumerate(staff_list):
            for shift_code, required_skill in skill_map.items():
                if shift_code in shift_to_idx:
                    sh_idx = shift_to_idx[shift_code]
                    if not staff.has_skill(required_skill):
                        for d in range(1, num_days + 1):
                            self.model.Add(self.shift_vars[(s_idx, d, sh_idx)] == 0)

    def _build_forbidden_constraint(self, constraint: Constraint,
                                   staff_list: List[StaffInfo], num_days: int,
                                   all_shifts: List[str]):
        """금지 제약 (NG 시프트)"""
        # NG 제약은 입력 데이터에서 처리되므로 여기서는 패스
        pass

    def _build_preference_constraint(self, constraint: Constraint,
                                    staff_list: List[StaffInfo], num_days: int,
                                    all_shifts: List[str], weight: Optional[int]):
        """선호 제약"""
        rule = constraint.get_rule()

        if rule.get("prefer_full_weekend_off_or_work"):
            self._add_weekend_preference(staff_list, num_days, all_shifts, weight or 10000)

    def _add_weekend_preference(self, staff_list: List[StaffInfo], num_days: int,
                               all_shifts: List[str], weight: int):
        """주말 전체 휴무 또는 전체 근무 선호"""
        from datetime import date
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_indices = [shift_to_idx.get(SHIFT_OFF), shift_to_idx.get(SHIFT_PUBLIC_OFF)]
        off_indices = [i for i in off_indices if i is not None]

        if not self.solver.input:
            return

        year = self.solver.input.year
        month = self.solver.input.month

        # 주말 쌍 찾기
        weekends = []
        d = 1
        while d <= num_days:
            try:
                dt = date(year, month, d)
                if dt.weekday() == 5:  # 토요일
                    if d + 1 <= num_days:
                        weekends.append((d, d + 1))
            except ValueError:
                pass
            d += 1

        for s_idx in range(len(staff_list)):
            for sat, sun in weekends:
                # 토요일 휴무 여부
                sat_off = self.model.NewBoolVar(f"sat_off_s{s_idx}_d{sat}")
                sat_off_vars = [self.shift_vars[(s_idx, sat, off_i)] for off_i in off_indices]
                if sat_off_vars:
                    self.model.Add(sum(sat_off_vars) >= 1).OnlyEnforceIf(sat_off)
                    self.model.Add(sum(sat_off_vars) == 0).OnlyEnforceIf(sat_off.Not())

                # 일요일 휴무 여부
                sun_off = self.model.NewBoolVar(f"sun_off_s{s_idx}_d{sun}")
                sun_off_vars = [self.shift_vars[(s_idx, sun, off_i)] for off_i in off_indices]
                if sun_off_vars:
                    self.model.Add(sum(sun_off_vars) >= 1).OnlyEnforceIf(sun_off)
                    self.model.Add(sum(sun_off_vars) == 0).OnlyEnforceIf(sun_off.Not())

                # 분할 주말 페널티 (한쪽만 휴무)
                split_penalty = self.model.NewBoolVar(f"split_weekend_s{s_idx}_d{sat}")
                self.model.Add(sat_off + sun_off == 1).OnlyEnforceIf(split_penalty)
                self.model.Add(sat_off + sun_off != 1).OnlyEnforceIf(split_penalty.Not())
                self.solver.penalty_vars.append((split_penalty, weight))

    def _build_balance_constraint(self, constraint: Constraint,
                                  staff_list: List[StaffInfo], num_days: int,
                                  all_shifts: List[str], weight: Optional[int]):
        """균형 제약"""
        rule = constraint.get_rule()

        if rule.get("target_off_days_field"):
            self._add_target_off_balance(staff_list, num_days, all_shifts, weight or 30000)

        if rule.get("balance_shifts"):
            shifts_to_balance = rule.get("balance_shifts", [])
            skill_filter = rule.get("among_staff_with_skill")
            self._add_shift_balance(staff_list, num_days, all_shifts, shifts_to_balance,
                                   skill_filter, weight or 20000)

        if rule.get("balance_weekend_work"):
            self._add_weekend_balance(staff_list, num_days, all_shifts, weight or 15000)

    def _add_target_off_balance(self, staff_list: List[StaffInfo], num_days: int,
                               all_shifts: List[str], weight: int):
        """목표 휴일 수 균형"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_indices = [shift_to_idx.get(SHIFT_OFF), shift_to_idx.get(SHIFT_PUBLIC_OFF)]
        off_indices = [i for i in off_indices if i is not None]

        for s_idx, staff in enumerate(staff_list):
            target = staff.target_off
            off_count = sum(
                self.shift_vars[(s_idx, d, off_i)]
                for d in range(1, num_days + 1)
                for off_i in off_indices
            )

            deviation = self.model.NewIntVar(0, num_days, f"off_dev_balance_s{s_idx}")
            self.model.AddAbsEquality(deviation, off_count - target)
            self.solver.penalty_vars.append((deviation, weight))

    def _add_shift_balance(self, staff_list: List[StaffInfo], num_days: int,
                          all_shifts: List[str], shifts_to_balance: List[str],
                          skill_filter: Optional[str], weight: int):
        """특정 시프트 균형 배분"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        balance_indices = [shift_to_idx[s] for s in shifts_to_balance if s in shift_to_idx]

        if not balance_indices:
            return

        # 대상 스태프 필터링
        eligible_staff = []
        for s_idx, staff in enumerate(staff_list):
            if skill_filter is None or staff.has_skill(skill_filter):
                eligible_staff.append(s_idx)

        if len(eligible_staff) < 2:
            return

        # 각 스태프의 해당 시프트 총 횟수
        shift_counts = []
        for s_idx in eligible_staff:
            count = sum(
                self.shift_vars[(s_idx, d, sh_idx)]
                for d in range(1, num_days + 1)
                for sh_idx in balance_indices
            )
            shift_counts.append(count)

        # 평균에서의 편차 최소화
        avg = self.model.NewIntVar(0, num_days * len(balance_indices), "balance_avg")
        total = sum(shift_counts)

        for s_idx_in_list, s_idx in enumerate(eligible_staff):
            deviation = self.model.NewIntVar(0, num_days, f"shift_balance_dev_s{s_idx}")
            # 간단한 편차 계산 (정확한 평균 대신 근사)
            self.model.AddAbsEquality(
                deviation,
                shift_counts[s_idx_in_list] * len(eligible_staff) - total
            )
            self.solver.penalty_vars.append((deviation, weight // len(eligible_staff)))

    def _add_weekend_balance(self, staff_list: List[StaffInfo], num_days: int,
                            all_shifts: List[str], weight: int):
        """주말 근무 균형"""
        from datetime import date
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        off_indices = [shift_to_idx.get(SHIFT_OFF), shift_to_idx.get(SHIFT_PUBLIC_OFF)]
        off_indices = [i for i in off_indices if i is not None]

        if not self.solver.input:
            return

        year = self.solver.input.year
        month = self.solver.input.month

        # 주말 날짜 찾기
        weekend_days = []
        for d in range(1, num_days + 1):
            try:
                dt = date(year, month, d)
                if dt.weekday() >= 5:  # 토/일
                    weekend_days.append(d)
            except ValueError:
                pass

        if not weekend_days:
            return

        # 각 스태프의 주말 근무 횟수
        weekend_work_counts = []
        for s_idx in range(len(staff_list)):
            work_count = 0
            for d in weekend_days:
                is_working = self.model.NewBoolVar(f"weekend_work_s{s_idx}_d{d}")
                off_vars = [self.shift_vars[(s_idx, d, off_i)] for off_i in off_indices]
                if off_vars:
                    self.model.Add(sum(off_vars) == 0).OnlyEnforceIf(is_working)
                    self.model.Add(sum(off_vars) >= 1).OnlyEnforceIf(is_working.Not())
                    work_count += is_working
            weekend_work_counts.append(work_count)

        # 균형 페널티
        total = sum(weekend_work_counts)
        for s_idx, count in enumerate(weekend_work_counts):
            deviation = self.model.NewIntVar(0, len(weekend_days), f"weekend_balance_dev_s{s_idx}")
            self.model.AddAbsEquality(
                deviation,
                count * len(staff_list) - total
            )
            self.solver.penalty_vars.append((deviation, weight // len(staff_list)))

    def _build_coverage_constraint(self, constraint: Constraint,
                                   staff_list: List[StaffInfo], num_days: int,
                                   all_shifts: List[str], night_shifts: List[str],
                                   weight: Optional[int]):
        """커버리지 제약"""
        rule = constraint.get_rule()

        if rule.get("min_staff_per_day"):
            min_staff = rule.get("min_staff_per_day", 3)
            exclude = rule.get("exclude_shifts", [SHIFT_OFF, SHIFT_PUBLIC_OFF])
            self._add_min_coverage(staff_list, num_days, all_shifts, min_staff, exclude, weight)

        if rule.get("shift_code") and rule.get("exactly_per_day"):
            shift_code = rule.get("shift_code")
            count = rule.get("exactly_per_day")
            self._add_exact_shift_coverage(staff_list, num_days, all_shifts, shift_code, count, weight)

        if rule.get("on_closed_days") and rule.get("night_shift_count"):
            night_count = rule.get("night_shift_count", 2)
            self._add_closed_day_night_coverage(staff_list, num_days, all_shifts, night_shifts, night_count, weight)

    def _add_min_coverage(self, staff_list: List[StaffInfo], num_days: int,
                         all_shifts: List[str], min_staff: int,
                         exclude_shifts: List[str], weight: Optional[int]):
        """일별 최소 인원 제약"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        exclude_indices = [shift_to_idx[s] for s in exclude_shifts if s in shift_to_idx]

        for d in range(1, num_days + 1):
            working_staff = []
            for s_idx in range(len(staff_list)):
                is_working = self.model.NewBoolVar(f"coverage_work_s{s_idx}_d{d}")
                exclude_vars = [self.shift_vars[(s_idx, d, ex_i)] for ex_i in exclude_indices]
                if exclude_vars:
                    self.model.Add(sum(exclude_vars) == 0).OnlyEnforceIf(is_working)
                    self.model.Add(sum(exclude_vars) >= 1).OnlyEnforceIf(is_working.Not())
                working_staff.append(is_working)

            if weight:  # 소프트 제약
                shortage = self.model.NewIntVar(0, len(staff_list), f"coverage_shortage_d{d}")
                self.model.Add(shortage >= min_staff - sum(working_staff))
                self.model.Add(shortage >= 0)
                self.solver.penalty_vars.append((shortage, weight))
            else:  # 하드 제약
                self.model.Add(sum(working_staff) >= min_staff)

    def _add_exact_shift_coverage(self, staff_list: List[StaffInfo], num_days: int,
                                  all_shifts: List[str], shift_code: str,
                                  count: int, weight: Optional[int]):
        """특정 시프트 정확히 N명"""
        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}

        if shift_code not in shift_to_idx:
            return

        sh_idx = shift_to_idx[shift_code]

        for d in range(1, num_days + 1):
            shift_count = sum(self.shift_vars[(s_idx, d, sh_idx)] for s_idx in range(len(staff_list)))

            if weight:  # 소프트 제약
                deviation = self.model.NewIntVar(0, len(staff_list), f"exact_coverage_dev_{shift_code}_d{d}")
                self.model.AddAbsEquality(deviation, shift_count - count)
                self.solver.penalty_vars.append((deviation, weight))
            else:  # 하드 제약
                self.model.Add(shift_count == count)

    def _add_closed_day_night_coverage(self, staff_list: List[StaffInfo], num_days: int,
                                       all_shifts: List[str], night_shifts: List[str],
                                       night_count: int, weight: Optional[int]):
        """휴관일 야간 인원"""
        if not self.solver.input:
            return

        closed_days = self.solver.input.closed_days
        if not closed_days:
            return

        shift_to_idx = {s: i for i, s in enumerate(all_shifts)}
        night_indices = [shift_to_idx[s] for s in night_shifts if s in shift_to_idx]

        for d in closed_days:
            if 1 <= d <= num_days:
                night_staff_count = sum(
                    self.shift_vars[(s_idx, d, n_idx)]
                    for s_idx in range(len(staff_list))
                    for n_idx in night_indices
                )

                if weight:
                    deviation = self.model.NewIntVar(0, len(staff_list), f"closed_night_dev_d{d}")
                    self.model.AddAbsEquality(deviation, night_staff_count - night_count)
                    self.solver.penalty_vars.append((deviation, weight))
                else:
                    self.model.Add(night_staff_count == night_count)
