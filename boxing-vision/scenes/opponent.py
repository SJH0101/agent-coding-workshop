"""
Opponent AI — 패턴 기반 복싱 상대.
완전 랜덤 X, 정해진 패턴 로테이션 + 약간의 랜덤성.
텔레그래프(공격 전 예고 모션) 존재.
"""

import random
import math


class Opponent:
    """
    상대 선수.
    - 패턴 로테이션으로 공격
    - 각 공격마다 텔레그래프(예고) → 실제 공격 순서
    - 체력 관리
    """

    def __init__(self, hp: int = 100):
        self.hp = hp
        self.max_hp = hp

        # 패턴 로테이션 (3~4개 패턴을 순환)
        self.patterns = [
            ["jab", "jab", "straight"],
            ["straight", "body"],
            ["jab", "body", "straight"],
            ["body", "jab", "jab", "straight"],
        ]
        self._pattern_idx = 0
        self._move_idx = 0

        # 상태 머신
        self.state = "idle"          # idle → telegraph → attacking → recovering → idle
        self.current_attack = None    # 현재 공격 종류
        self.state_timer = 0.0        # 상태 지속 시간
        self._damage_dealt = False    # 현재 공격에서 데미지를 이미 줬는지

        # 타이밍 (초)
        self.idle_min = 0.8
        self.idle_max = 1.5
        self.telegraph_duration = 0.35
        self.attack_duration = 0.25
        self.recover_duration = 0.3

        # 애니메이션 보간 (0~1)
        self.anim_t = 0.0

    def reset(self):
        self.hp = self.max_hp
        self.state = "idle"
        self.current_attack = None
        self.state_timer = 0.0
        self.anim_t = 0.0
        self._pattern_idx = 0
        self._move_idx = 0

    def update(self, dt: float):
        """매 프레임 호출. dt = delta time (초)."""
        self.state_timer += dt

        if self.state == "idle":
            idle_dur = self._idle_duration()
            self.anim_t = self.state_timer / idle_dur
            if self.state_timer >= idle_dur:
                self._start_telegraph()

        elif self.state == "telegraph":
            self.anim_t = self.state_timer / self.telegraph_duration
            if self.state_timer >= self.telegraph_duration:
                self._start_attack()

        elif self.state == "attacking":
            self.anim_t = self.state_timer / self.attack_duration
            if self.state_timer >= self.attack_duration:
                self._start_recover()

        elif self.state == "recovering":
            self.anim_t = self.state_timer / self.recover_duration
            if self.state_timer >= self.recover_duration:
                self._next_move()
                self.state = "idle"
                self.state_timer = 0.0
                self.anim_t = 0.0

    def _idle_duration(self) -> float:
        return random.uniform(self.idle_min, self.idle_max)

    def _start_telegraph(self):
        """다음 공격 선택 + 텔레그래프 시작."""
        pattern = self.patterns[self._pattern_idx % len(self.patterns)]
        self.current_attack = pattern[self._move_idx % len(pattern)]
        self.state = "telegraph"
        self.state_timer = 0.0
        self.anim_t = 0.0

    def _start_attack(self):
        self.state = "attacking"
        self.state_timer = 0.0
        self.anim_t = 0.0
        self._damage_dealt = False

    def _start_recover(self):
        self.state = "recovering"
        self.state_timer = 0.0
        self.anim_t = 0.0

    def _next_move(self):
        self._move_idx += 1
        if self._move_idx >= len(self.patterns[self._pattern_idx % len(self.patterns)]):
            self._move_idx = 0
            self._pattern_idx += 1

    def try_deal_damage(self, dmg: int = 10) -> int:
        """공격당 1회만 데미지. 반환: 실제로 적용된 데미지 (0이면 이미 줌)."""
        if self.state == "attacking" and not self._damage_dealt:
            self._damage_dealt = True
            return dmg
        return 0

    def is_recovering(self) -> bool:
        return self.state == "recovering"

    def telegraph_pct(self) -> float:
        """텔레그래프 진행률 0~1. 애니메이션용."""
        if self.state == "telegraph":
            return min(self.anim_t, 1.0)
        return 0.0

    def attack_pct(self) -> float:
        """공격 진행률 0~1."""
        if self.state == "attacking":
            return min(self.anim_t, 1.0)
        return 0.0

    def take_damage(self, dmg: int = 10):
        self.hp = max(0, self.hp - dmg)

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0
