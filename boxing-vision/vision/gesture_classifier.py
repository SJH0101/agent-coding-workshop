"""
Gesture Classifier — 어깨-손목 거리 기반 복싱 동작 판정.
왼손 = 잽, 오른손 = 스트레이트, 양손 동시 = 어퍼컷.
위빙 → 바디슬립 (어깨 중심 이동).
"""

import math
from collections import deque


class GestureClassifier:
    """
    어깨-손목 거리 변화로 펀치 감지.
    - 왼손(MediaPipe 오른손) = 잽
    - 오른손(MediaPipe 왼손) = 스트레이트
    - 양손 동시 상승 = 어퍼컷
    - 어깨 중심 이동 = 바디슬립/위빙
    """

    def __init__(self, buffer_size: int = 8, cooldown: float = 0.4):
        self.buffer_size = buffer_size
        self.cooldown = cooldown
        self._last_time = {"jab": 0.0, "straight": 0.0, "weave": 0.0, "uppercut": 0.0}
        self._weave_block_until = 0.0

        self._dist_buf = {
            "left": deque(maxlen=buffer_size),
            "right": deque(maxlen=buffer_size),
        }
        # 어깨 중심 버퍼 (위빙/슬립 감지용)
        self._shoulder_cx_buf = deque(maxlen=buffer_size)
        self._prev_nose_x = None

        # 양손 동시 펀치 감지용
        self._both_punch_window = 0.3
        self._last_extend_time = {"left": 0.0, "right": 0.0}
        self._last_extend_vel = {"left": 0.0, "right": 0.0}

    def _cooldown_ok(self, move: str, now: float) -> bool:
        return (now - self._last_time.get(move, 0.0)) >= self.cooldown

    @staticmethod
    def _sw_dist(shoulder: dict, wrist: dict) -> float:
        dx = shoulder["x"] - wrist["x"]
        dy = shoulder["y"] - wrist["y"]
        return math.hypot(dx, dy)

    def _extend_velocity(self, hand: str) -> float:
        buf = self._dist_buf[hand]
        if len(buf) < 4:
            return 0.0
        t0, d0 = buf[-4]
        t1, d1 = buf[-1]
        dt = t1 - t0
        if dt < 0.01:
            return 0.0
        return (d1 - d0) / dt

    def detect(self, lm: dict, now: float) -> str | None:
        if lm is None:
            return None

        # 거리 업데이트
        for side in ("left", "right"):
            sh = lm[f"{side}_shoulder"]
            wr = lm[f"{side}_wrist"]
            if sh["v"] > 0.5 and wr["v"] > 0.5:
                d = self._sw_dist(sh, wr)
                self._dist_buf[side].append((now, d))

        # 어깨 중심 업데이트
        scx = (lm["left_shoulder"]["x"] + lm["right_shoulder"]["x"]) / 2
        if lm["left_shoulder"]["v"] > 0.5 and lm["right_shoulder"]["v"] > 0.5:
            self._shoulder_cx_buf.append((now, scx))

        # 위빙/슬립
        if self._check_weave(lm, now):
            self._weave_block_until = now + 0.5
            return "weave"

        # 위빙 후 0.5초간 펀치 차단
        if now < self._weave_block_until:
            return None

        # 어퍼컷 (양손 동시 상승)
        if self._check_uppercut(lm, now):
            return "uppercut"

        # 잽 (왼손/MediaPipe 오른손)
        if self._check_jab(lm, now):
            return "jab"

        # 스트레이트 (오른손/MediaPipe 왼손)
        if self._check_straight(lm, now):
            return "straight"

        return None

    # ── 개별 동작 ──

    def _check_jab(self, lm: dict, now: float) -> bool:
        if not self._cooldown_ok("jab", now):
            return False
        if self._extend_punch("right", min_vel=150, min_ratio=1.15, now=now):
            self._last_time["jab"] = now
            return True
        return False

    def _check_straight(self, lm: dict, now: float) -> bool:
        if not self._cooldown_ok("straight", now):
            return False
        if self._extend_punch("left", min_vel=120, min_ratio=1.20, now=now):
            self._last_time["straight"] = now
            return True
        return False

    def _extend_punch(self, hand: str, min_vel: float, min_ratio: float, now: float) -> bool:
        buf = self._dist_buf[hand]
        if len(buf) < 5:
            return False
        t0, d0 = buf[-5]
        t1, d1 = buf[-1]
        dt = t1 - t0
        if dt < 0.005:
            return False
        vel = (d1 - d0) / dt
        ratio = d1 / max(1, d0)
        if vel > min_vel and ratio > min_ratio:
            self._last_extend_time[hand] = now
            self._last_extend_vel[hand] = vel
            return True
        return False

    def _check_uppercut(self, lm: dict, now: float) -> bool:
        """양손 동시에 위로 올리는 모션 = 어퍼컷."""
        if not self._cooldown_ok("uppercut", now):
            return False

        # 최근 0.3초 내에 양손 모두 익스텐션이 있었는지
        l_recent = (now - self._last_extend_time["left"]) < self._both_punch_window
        r_recent = (now - self._last_extend_time["right"]) < self._both_punch_window

        if l_recent and r_recent:
            # 양손 손목이 모두 어깨 위에 있는지 (어퍼컷 자세)
            sy = (lm["left_shoulder"]["y"] + lm["right_shoulder"]["y"]) / 2
            lw = lm["left_wrist"]
            rw = lm["right_wrist"]
            if lw["v"] > 0.5 and rw["v"] > 0.5:
                if lw["y"] < sy - 30 and rw["y"] < sy - 30:
                    self._last_time["uppercut"] = now
                    return True
        return False

    def _check_weave(self, lm: dict, now: float) -> bool:
        """
        바디 슬립: 어깨 중심의 급격한 좌우 이동 감지.
        반환과 함께 슬립 방향 기록 (양수=오른쪽, 음수=왼쪽).
        """
        if not self._cooldown_ok("weave", now):
            return False

        buf = self._shoulder_cx_buf
        if len(buf) < 5:
            return False

        t0, cx0 = buf[-5]
        t1, cx1 = buf[-1]
        dt = t1 - t0
        if dt < 0.01:
            return False

        # 어깨 중심 이동 속도 (px/s)
        slip_vel = (cx1 - cx0) / dt
        self._last_slip_dir = slip_vel  # 양수=오른쪽, 음수=왼쪽

        if abs(slip_vel) > 200:
            self._last_time["weave"] = now
            return True
        return False

    def get_slip_direction(self) -> float:
        """마지막 슬립 방향. 양수=오른쪽, 음수=왼쪽."""
        return getattr(self, "_last_slip_dir", 0.0)

    def detect_jab(self, lm: dict, now: float) -> bool:
        return self._check_jab(lm, now)