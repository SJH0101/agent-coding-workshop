"""
Fight Scene — Pygame 1인칭 복싱 게임 (Wii 스타일).
고퀄리티 그래픽 + 매끄러운 애니메이션 + 플레이어 캐릭터.
"""

import math
import random
import threading
import time as time_module

import cv2
import pygame

from vision.pose_tracker import PoseTracker
from vision.gesture_classifier import GestureClassifier
from scenes.opponent import Opponent

# ── 공유 상태 ──


class SharedPose:
    def __init__(self):
        self._lock = threading.Lock()
        self.frame = None
        self.last_gesture = None
        self.gesture_time = 0.0
        self.lm = None
        self.running = True
        self.slip_dir = 0.0

    def update(self, frame, gesture, gesture_time, lm):
        with self._lock:
            self.frame = frame
            self.last_gesture = gesture
            self.gesture_time = gesture_time
            self.lm = lm

    def read(self):
        with self._lock:
            return self.frame, self.last_gesture, self.gesture_time

    def read_lm(self):
        with self._lock:
            return self.lm

    def stop(self):
        with self._lock:
            self.running = False

    @property
    def is_running(self):
        with self._lock:
            return self.running


def camera_thread_func(cam_index: int, shared: SharedPose):
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("[Camera] 웹캠 열기 실패")
        shared.running = False
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 최소화
    tracker = PoseTracker(model_path="assets/pose_landmarker_heavy.task")
    classifier = GestureClassifier()
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    skip_counter = 0

    while shared.is_running:
        ret, frame = cap.read()
        if not ret:
            continue

        # 메인 스레드가 히트스탑 중이면 프레임 스킵 (버퍼 비우기)
        skip_counter += 1
        if skip_counter % 2 != 0:
            continue

        frame = cv2.flip(frame, 1)
        annotated, landmarks = tracker.process_frame(frame)
        lm = None
        gesture = None
        now = time_module.time()
        if landmarks:
            lm = tracker.get_landmark_dict(landmarks, fw, fh)
            if lm:
                gesture = classifier.detect(lm, now)
                shared.slip_dir = classifier.get_slip_direction()
        shared.update(annotated, gesture, now, lm)

    cap.release()
    tracker.release()


# ── 색상 ──

C = {
    "bg": (12, 12, 28),
    "ring_floor": (55, 45, 75),
    "ring_ropes": (180, 60, 60),
    "red": (255, 40, 60),
    "blue": (40, 140, 255),
    "green": (50, 255, 120),
    "yellow": (255, 220, 40),
    "purple": (180, 40, 255),
    "white": (230, 230, 240),
    "dim": (100, 100, 130),
    "skin": (220, 190, 170),
    "skin_shadow": (180, 150, 130),
    "glove_l": (240, 50, 60),
    "glove_r": (50, 150, 255),
    "body": (100, 80, 120),
    "body_highlight": (140, 120, 160),
}

DAMAGE = {"jab": 8, "straight": 15, "uppercut": 40}

# ── 이지징 함수 ──

def ease_out(t):
    return 1.0 - (1.0 - t) ** 3

def lerp(a, b, t):
    return a + (b - a) * t


# ── 파티클 시스템 ──


class Particle:
    def __init__(self, x, y, color, vx, vy, life):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.size = random.uniform(2, 5)

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += 200 * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        alpha = int(255 * (self.life / self.max_life))
        c = (*self.color[:3], alpha)
        size = int(self.size * (self.life / self.max_life))
        if size > 0:
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, c, (size, size), size)
            surf.blit(s, (self.x - size, self.y - size))


# ── UI 그리기 ──


def draw_hp_bar(surf, x, y, w, h, ratio, color, label):
    bg_rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (30, 30, 45), bg_rect, border_radius=6)
    fill_w = int(w * max(0, ratio))
    if fill_w > 0:
        fill_rect = pygame.Rect(x, y, fill_w, h)
        pygame.draw.rect(surf, color, fill_rect, border_radius=6)
    pygame.draw.rect(surf, color, bg_rect, 2, border_radius=6)
    font = pygame.font.Font(None, 22)
    txt = font.render(label, True, C["white"])
    surf.blit(txt, (x, y - 24))


# ── 메인 전투 ──


def run_fight():
    pygame.init()
    W, H = 1280, 720
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Boxing Vision")
    clock = pygame.time.Clock()

    # ── 정적 배경 미리 렌더링 (렉 방지) ──
    bg_cache = pygame.Surface((W, H))

    # 체육관 벽
    for y in range(H):
        t = y / H
        c = (int(15 + 20 * t), int(12 + 18 * t), int(30 + 25 * t))
        pygame.draw.line(bg_cache, c, (0, y), (W, y))

    # 천장 조명
    light_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for lx in [W // 4, W // 2, 3 * W // 4]:
        for r in range(300, 50, -15):
            a = max(0, 15 - r // 25)
            pygame.draw.circle(light_surf, (200, 180, 150, a), (lx, -50), r)
    bg_cache.blit(light_surf, (0, 0))

    # UNIST 배너
    banner = pygame.Surface((400, 60), pygame.SRCALPHA)
    banner.fill((30, 20, 50, 200))
    bg_cache.blit(banner, (W // 2 - 200, 30))
    unist_font = pygame.font.Font(None, 42)
    unist_txt = unist_font.render("UNIST BOXING GYM", True, (220, 200, 180))
    bg_cache.blit(unist_txt, (W // 2 - unist_txt.get_width() // 2, 38))
    tag_font = pygame.font.Font(None, 20)
    tag = tag_font.render("Ulsan National Institute of Science & Technology", True, (140, 130, 150))
    bg_cache.blit(tag, (W // 2 - tag.get_width() // 2, 78))

    # 링 포스트
    for px, py in [(120, 300), (1160, 300)]:
        pygame.draw.rect(bg_cache, (180, 60, 60), (px - 8, py, 16, 200))
        pygame.draw.rect(bg_cache, (220, 100, 100), (px - 4, py, 8, 200))
        for cy in [py + 20, py + 60, py + 100]:
            pygame.draw.circle(bg_cache, (200, 50, 50), (px, cy), 14)
            pygame.draw.circle(bg_cache, (240, 100, 100), (px, cy), 8)

    # 링 로프
    for ry in [320, 365, 410]:
        pygame.draw.line(bg_cache, (200, 60, 60), (120, ry), (1160, ry), 5)
        pygame.draw.line(bg_cache, (240, 100, 100), (120, ry), (1160, ry), 2)

    # 링 바닥
    floor_surf = pygame.Surface((1100, 260), pygame.SRCALPHA)
    for r in range(130, 0, -5):
        a = max(0, 60 - r // 3)
        c = (40 + r // 2, 35 + r // 3, 65 + r // 4, a)
        pygame.draw.ellipse(floor_surf, c, (550 - r, 130 - r // 2, r * 2, r + 20))
    bg_cache.blit(floor_surf, (W // 2 - 550, 440))
    floor_outline = pygame.Rect(W // 2 - 450, 460, 900, 220)
    pygame.draw.ellipse(bg_cache, (80, 60, 100), floor_outline, 3)
    logo = pygame.font.Font(None, 72)
    lg = logo.render("U", True, (60, 50, 80))
    lg.set_alpha(20)
    bg_cache.blit(lg, (W // 2 - 20, 510))

    # ── HP 바 미리 렌더링용 ──

    shared = SharedPose()
    cam_thread = threading.Thread(target=camera_thread_func, args=(1, shared), daemon=True)
    cam_thread.start()

    opponent = Opponent(hp=200)
    player_hp = 200
    MAX_HP = 200

    shake = pygame.math.Vector2(0, 0)
    shake_timer = 0.0
    hit_flash = 0.0
    hit_landed = 0.0
    particles = []
    hitstop_timer = 0.0

    is_weaving = False
    weave_timer = 0.0
    opp_recoil = 0.0

    round_num = 1

    font_large = pygame.font.Font(None, 80)
    font_big = pygame.font.Font(None, 60)
    font_mid = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)

    pip_w, pip_h = 220, 165
    pip_x, pip_y = W - pip_w - 24, H - pip_h - 24

    game_over = False
    game_result = ""
    prev_gesture = None

    player_punch = {"left": 0.0, "right": 0.0}

    # 콤보 시스템
    combo = 0
    combo_timer = 0.0
    COMBO_TIMEOUT = 2.0  # 초, 이후 리셋
    last_hit_time = 0.0

    # 표시용 타이머 (느리게 페이드)
    gesture_display_txt = ""
    gesture_display_timer = 0.0
    GESTURE_DISPLAY_DURATION = 1.5
    GESTURE_DISPLAY_FADE = 0.5  # 마지막 0.5초 페이드

    combo_display_timer = 0.0
    COMBO_DISPLAY_DURATION = 3.0
    last_combo = 0

    time_module.sleep(0.8)

    while True:
        dt_raw = clock.tick(60) / 1000.0
        if hitstop_timer > 0:
            hitstop_timer -= dt_raw
            dt = 0.0
        else:
            dt = min(dt_raw, 0.05)
        now = time_module.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                shared.stop(); pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    shared.stop(); pygame.quit(); return
                if game_over and event.key == pygame.K_r:
                    opponent.reset()
                    player_hp = 200
                    game_over = False
                    game_result = ""
                    shake_timer = 0.0
                    hit_flash = 0.0
                    hit_landed = 0.0
                    opp_recoil = 0.0
                    combo = 0
                    particles.clear()

        frame, gesture, gesture_time = shared.read()

        if gesture == "weave":
            is_weaving = True
            weave_timer = 0.3
            # 마지막 슬립 방향 저장
            _last_slip_dir = getattr(shared, 'slip_dir', 0.0)
        if is_weaving:
            weave_timer -= dt
            if weave_timer <= 0:
                is_weaving = False

        if not game_over:
            opponent.update(dt)

        punch_landed = False
        if not game_over and gesture:
            if gesture in ("jab", "straight", "uppercut") and prev_gesture != gesture:
                if now - gesture_time < 0.15:
                    # 콤보 계산
                    if now - last_hit_time < COMBO_TIMEOUT:
                        combo += 1
                    else:
                        combo = 1
                    last_hit_time = now
                    combo_timer = COMBO_TIMEOUT

                    # 데미지 (콤보 보너스)
                    base = DAMAGE.get(gesture, 10)
                    combo_bonus = 1.0 + (combo - 1) * 0.15  # 콤보당 +15%
                    dmg = int(base * combo_bonus)
                    opponent.take_damage(dmg)

                    hit_landed = 0.2
                    opp_recoil = 1.0
                    shake_timer = 0.12
                    shake.x, shake.y = random.randint(-10, 10), random.randint(-5, 5)
                    hitstop_timer = 0.05 + (0.02 if gesture == "uppercut" else 0)
                    punch_landed = True
                    # 표시 타이머 갱신
                    gesture_display_txt = gesture.upper()
                    gesture_display_timer = GESTURE_DISPLAY_DURATION
                    last_combo = combo
                    combo_display_timer = COMBO_DISPLAY_DURATION
                    hand_key = {"jab": "left", "straight": "right", "uppercut": "left"}.get(gesture, "left")
                    player_punch[hand_key] = 0.3
                    cx = W // 2
                    p_count = 30 if gesture == "uppercut" else 20
                    for _ in range(p_count):
                        particles.append(Particle(
                            cx + random.randint(-40, 40), 280 + random.randint(-40, 40),
                            (255, 255, 100),
                            random.uniform(-300, 300), random.uniform(-300, 100),
                            random.uniform(0.2, 0.5),
                        ))
        prev_gesture = gesture

        if not game_over:
            dmg = opponent.try_deal_damage(10)
            if dmg > 0 and not is_weaving:
                player_hp = max(0, player_hp - dmg)
                hit_flash = 0.25
                shake_timer = 0.18
                shake.x, shake.y = random.randint(-15, 15), random.randint(-8, 8)
                hitstop_timer = 0.08
                for _ in range(25):
                    particles.append(Particle(
                        W // 2 + random.randint(-60, 60), 300 + random.randint(-30, 30),
                        (255, 50, 50),
                        random.uniform(-200, 200), random.uniform(-200, 200),
                        random.uniform(0.2, 0.5),
                    ))

        if shake_timer > 0:
            shake_timer -= dt
        else:
            shake.x = shake.y = 0
        if hit_flash > 0:
            hit_flash -= dt
        if hit_landed > 0:
            hit_landed -= dt
        if opp_recoil > 0:
            opp_recoil -= dt * 3.0
            opp_recoil = max(0, opp_recoil)

        for hand in ("left", "right"):
            if player_punch[hand] > 0:
                player_punch[hand] -= dt

        # 콤보 타이머 감소
        if combo > 0:
            combo_timer -= dt
            if combo_timer <= 0:
                combo = 0

        # 표시 타이머 감소
        if gesture_display_timer > 0:
            gesture_display_timer -= dt
        if combo_display_timer > 0:
            combo_display_timer -= dt

        particles = [p for p in particles if p.alive]
        for p in particles:
            p.update(dt)

        if not game_over:
            if opponent.is_dead:
                game_over = True
                game_result = "YOU WIN!"
            elif player_hp <= 0:
                game_over = True
                game_result = "YOU LOSE..."

        # ── 배경 (캐시된 것 블릿) ──
        screen.blit(bg_cache, (0, 0))

        soff = (int(shake.x * (1 if shake_timer > 0.18 else shake_timer / 0.18)),
                int(shake.y * (1 if shake_timer > 0.18 else shake_timer / 0.18)))

        _draw_opponent(screen, opponent, W, H, opp_recoil, dt)

        lm = shared.read_lm()
        _draw_player(screen, W, H, lm, player_punch, is_weaving, weave_timer, now)

        if hit_landed > 0:
            a = int(200 * (hit_landed / 0.2))
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(ov, (255, 255, 100, a // 2), (W // 2 + soff[0], 300 + soff[1]), 80)
            screen.blit(ov, (0, 0))

        if hit_flash > 0:
            a = int(160 * (hit_flash / 0.25))
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 40, 40, a))
            screen.blit(ov, (0, 0))

        for p in particles:
            p.draw(screen)

        # ── 제스처 표시 (전용 타이머 + 페이드) ──
        if gesture_display_timer > 0 and gesture_display_txt:
            fade_t = max(0, gesture_display_timer - (GESTURE_DISPLAY_DURATION - GESTURE_DISPLAY_FADE))
            alpha = int(255 * min(1.0, fade_t / GESTURE_DISPLAY_FADE))
            if alpha > 0:
                gcols = {"JAB": C["yellow"], "STRAIGHT": C["blue"], "WEAVE": C["purple"], "UPPERCUT": (255, 100, 255)}
                col = gcols.get(gesture_display_txt, C["white"])
                txt = font_big.render(gesture_display_txt, True, col)
                txt.set_alpha(alpha)
                shadow = font_big.render(gesture_display_txt, True, (20, 20, 30))
                shadow.set_alpha(alpha)
                for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                    screen.blit(shadow, (W // 2 - txt.get_width() // 2 + dx + soff[0], 180 + soff[1] + dy))
                screen.blit(txt, (W // 2 - txt.get_width() // 2 + soff[0], 180 + soff[1]))

        # ── 콤보 표시 (전용 타이머 + 페이드) ──
        if combo_display_timer > 0 and last_combo >= 2:
            fade_t = max(0, combo_display_timer - (COMBO_DISPLAY_DURATION - 0.8))
            alpha = int(255 * min(1.0, fade_t / 0.8))
            if alpha > 0:
                combo_color = (min(255, 100 + last_combo * 30), max(50, 255 - last_combo * 20), 50)
                ctxt = font_mid.render(f"{last_combo} COMBO!", True, combo_color)
                ctxt.set_alpha(alpha)
                cshadow = font_mid.render(f"{last_combo} COMBO!", True, (20, 20, 30))
                cshadow.set_alpha(alpha)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    screen.blit(cshadow, (W // 2 - ctxt.get_width() // 2 + dx + soff[0], 130 + soff[1] + dy))
                screen.blit(ctxt, (W // 2 - ctxt.get_width() // 2 + soff[0], 130 + soff[1]))

        draw_hp_bar(screen, 60 + soff[0], 50 + soff[1], 380, 24, player_hp / MAX_HP, C["green"], "YOU")
        draw_hp_bar(screen, W - 440 + soff[0], 50 + soff[1], 380, 24, opponent.hp / opponent.max_hp, C["red"], "OPPONENT")

        rtxt = font_mid.render(f"ROUND {round_num}", True, C["dim"])
        screen.blit(rtxt, (W // 2 - rtxt.get_width() // 2 + soff[0], 16 + soff[1]))

        if frame is not None:
            pf = cv2.resize(frame, (pip_w, pip_h))
            pf = cv2.cvtColor(pf, cv2.COLOR_BGR2RGB)
            pf = pf.swapaxes(0, 1)
            ps = pygame.surfarray.make_surface(pf)
            screen.blit(ps, (pip_x + soff[0], pip_y + soff[1]))
            pygame.draw.rect(screen, C["blue"], (pip_x + soff[0], pip_y + soff[1], pip_w, pip_h), 2, border_radius=4)

        if game_over:
            col = C["green"] if "WIN" in game_result else C["red"]
            gt = font_large.render(game_result, True, col)
            screen.blit(gt, (W // 2 - gt.get_width() // 2, H // 2 - 60))
            rt = font_mid.render("Press R to restart | ESC to quit", True, C["dim"])
            screen.blit(rt, (W // 2 - rt.get_width() // 2, H // 2 + 20))

        pygame.display.flip()


# ── 상대 렌더링 ──


def _draw_opponent(surf, opp: Opponent, W: int, H: int, recoil: float, dt: float):
    cx, cy = W // 2, H // 2 - 20
    recoil_x = int(-30 * recoil)
    t_pct = ease_out(opp.telegraph_pct())
    a_pct = ease_out(opp.attack_pct())

    body_y = cy + 10 + recoil_x // 2
    body_rect = pygame.Rect(cx - 60 + recoil_x, body_y - 30, 120, 180)
    shadow_rect = body_rect.move(4, 6)
    pygame.draw.ellipse(surf, (20, 15, 30), shadow_rect)
    pygame.draw.ellipse(surf, C["body"], body_rect)
    pygame.draw.ellipse(surf, C["body_highlight"], body_rect, 2)

    head_cx = cx + recoil_x
    head_cy = cy - 60
    pygame.draw.circle(surf, (20, 15, 30), (head_cx + 3, head_cy + 4), 38)
    pygame.draw.circle(surf, C["skin"], (head_cx, head_cy), 38)
    pygame.draw.circle(surf, C["skin_shadow"], (head_cx, head_cy), 38, 3)
    pygame.draw.arc(surf, C["red"], (head_cx - 35, head_cy - 38, 70, 50), 0.2, math.pi - 0.2, 4)

    eye_off = recoil_x
    for ex in [-10, 10]:
        pygame.draw.circle(surf, C["red"], (head_cx + ex + eye_off, head_cy - 4), 5)
        pygame.draw.circle(surf, (255, 255, 255), (head_cx + ex + eye_off, head_cy - 4), 2)
    pygame.draw.line(surf, C["red"], (head_cx - 16 + eye_off, head_cy - 16),
                     (head_cx - 6 + eye_off, head_cy - 12), 3)
    pygame.draw.line(surf, C["red"], (head_cx + 16 + eye_off, head_cy - 16),
                     (head_cx + 6 + eye_off, head_cy - 12), 3)
    mouth_y = head_cy + 14
    pygame.draw.arc(surf, (150, 100, 80), (head_cx - 10 + eye_off, mouth_y - 4, 20, 10),
                    0.1, math.pi - 0.1, 2)

    l_shoulder = (cx - 55 + recoil_x, body_y + 5)
    r_shoulder = (cx + 55 + recoil_x, body_y + 5)
    l_guard = (l_shoulder[0] - 30, l_shoulder[1] + 10)
    r_guard = (r_shoulder[0] + 30, r_shoulder[1] + 10)
    l_fist = l_guard
    r_fist = r_guard

    if opp.state == "telegraph" and opp.current_attack:
        pull_back = 40 * t_pct
        if opp.current_attack in ("jab", "body"):
            l_fist = (l_shoulder[0] - 30 - int(pull_back), l_shoulder[1] + 10)
        else:
            r_fist = (r_shoulder[0] + 30 + int(pull_back), r_shoulder[1] + 10)

    if opp.state == "attacking":
        extend = 120 * a_pct
        if opp.current_attack == "jab":
            l_fist = (l_shoulder[0] - 10, l_shoulder[1] - 10 - int(extend * 0.5))
        elif opp.current_attack == "straight":
            r_fist = (r_shoulder[0] + 10, r_shoulder[1] - 10 - int(extend * 0.6))
            l_shoulder = (l_shoulder[0] - int(10 * a_pct), l_shoulder[1] + int(5 * a_pct))
        elif opp.current_attack == "body":
            l_fist = (l_shoulder[0] - 10, l_shoulder[1] + 50 + int(extend * 0.3))

    for shoulder, fist, color in [
        (l_shoulder, l_fist, C["skin"]),
        (r_shoulder, r_fist, C["skin"]),
    ]:
        for w in [14, 8]:
            pygame.draw.line(surf, C["skin_shadow"], shoulder, fist, w)
        pygame.draw.line(surf, color, shoulder, fist, 8)

    for fist, gcolor, gcolor2 in [
        (l_fist, C["glove_l"], (200, 30, 40)),
        (r_fist, C["glove_r"], (30, 110, 220)),
    ]:
        r = 18 + (6 if opp.state == "attacking" and a_pct > 0.5 else 0)
        pygame.draw.circle(surf, (20, 15, 30), (fist[0] + 3, fist[1] + 4), r)
        pygame.draw.circle(surf, gcolor, fist, r)
        pygame.draw.circle(surf, gcolor2, fist, r, 3)
        hl = (min(255, gcolor[0] + 80), min(255, gcolor[1] + 80), min(255, gcolor[2] + 80))
        pygame.draw.circle(surf, hl, (fist[0] - 4, fist[1] - 4), r // 3)

    if opp.state == "telegraph" and opp.current_attack:
        warn = opp.current_attack.upper()
        size = 28 + int(10 * t_pct)
        font = pygame.font.Font(None, size)
        wt = font.render(f"! {warn} !", True, C["yellow"])
        alpha = int(200 + 55 * math.sin(t_pct * math.pi * 6))
        wt.set_alpha(alpha)
        surf.blit(wt, (cx - wt.get_width() // 2, 160))

    if recoil > 0:
        dmg_font = pygame.font.Font(None, int(36 + 20 * recoil))
        dtxt = dmg_font.render("HIT!", True, C["yellow"])
        surf.blit(dtxt, (cx - dtxt.get_width() // 2, cy - 120 - int(40 * recoil)))


# ── 플레이어 캐릭터 렌더링 (1인칭 하단) ──


def _draw_player(surf, W: int, H: int, lm: dict | None, punch: dict,
                 is_weaving: bool = False, weave_timer: float = 0.0,
                 game_time: float = 0.0):
    """플레이어의 머리 + 팔 + 글러브를 1인칭 하단에서 그림."""
    cx = W // 2
    base_x = cx
    base_y = H - 60

    # 위빙 오프셋
    weave_off = 0
    body_weave = 0
    if is_weaving:
        weave_off = int(30 * math.sin(weave_timer * math.pi * 4))
        body_weave = int(15 * math.sin(weave_timer * math.pi * 4))

    # ── 머리 ──
    head_cx = base_x + weave_off
    head_cy = base_y - 120
    # 머리 그림자
    pygame.draw.circle(surf, (20, 15, 30), (head_cx + 2, head_cy + 3), 30)
    # 머리 본체
    pygame.draw.circle(surf, C["skin"], (head_cx, head_cy), 30)
    pygame.draw.circle(surf, C["skin_shadow"], (head_cx, head_cy), 30, 2)
    # 헤드기어
    pygame.draw.arc(surf, (60, 60, 60), (head_cx - 28, head_cy - 30, 56, 40), 0.1, math.pi - 0.1, 3)
    # 눈
    for ex in [-8, 8]:
        pygame.draw.circle(surf, (255, 255, 255), (head_cx + ex + weave_off // 3, head_cy - 2), 4)
        pygame.draw.circle(surf, (80, 80, 80), (head_cx + ex + weave_off // 3, head_cy - 2), 2)
    # 헤드기어 스트랩
    pygame.draw.line(surf, (60, 60, 60), (head_cx - 28, head_cy - 15), (base_x - 15, base_y - 35), 2)
    pygame.draw.line(surf, (60, 60, 60), (head_cx + 28, head_cy - 15), (base_x + 15, base_y - 35), 2)

    # ── 팔 ──
    l_t = min(1.0, punch["left"] / 0.3) if punch["left"] > 0 else 0.0
    r_t = min(1.0, punch["right"] / 0.3) if punch["right"] > 0 else 0.0

    l_guard = (base_x - 55 + body_weave, base_y - 80 + abs(body_weave) // 3)
    r_guard = (base_x + 55 + body_weave, base_y - 80 + abs(body_weave) // 3)

    l_ext = int(180 * (1.0 - (1.0 - l_t) ** 2)) if l_t > 0 else 0
    r_ext = int(220 * (1.0 - (1.0 - r_t) ** 2)) if r_t > 0 else 0

    l_fist = (l_guard[0], l_guard[1] - l_ext)
    r_fist = (r_guard[0], r_guard[1] - r_ext)

    l_shoulder = (base_x - 40 + body_weave, base_y)
    r_shoulder = (base_x + 40 + body_weave, base_y)

    for shoulder, fist, color in [
        (l_shoulder, l_fist, C["skin"]),
        (r_shoulder, r_fist, C["skin"]),
    ]:
        for w in [10, 6]:
            pygame.draw.line(surf, C["skin_shadow"], shoulder, fist, w)
        pygame.draw.line(surf, color, shoulder, fist, 6)

    for fist, gcolor, gcolor2 in [
        (l_fist, C["glove_l"], (200, 30, 40)),
        (r_fist, C["glove_r"], (30, 110, 220)),
    ]:
        r = 20 + (4 if l_ext > 50 else 0)
        pygame.draw.circle(surf, (20, 15, 30), (fist[0] + 2, fist[1] + 3), r)
        pygame.draw.circle(surf, gcolor, fist, r)
        pygame.draw.circle(surf, gcolor2, fist, r, 3)
        hl = (min(255, gcolor[0] + 80), min(255, gcolor[1] + 80), min(255, gcolor[2] + 80))
        pygame.draw.circle(surf, hl, (fist[0] - 3, fist[1] - 3), r // 3)

    font = pygame.font.Font(None, 16)
    for fist, label in [(l_fist, "L"), (r_fist, "R")]:
        lbl = font.render(label, True, (255, 255, 255))
        surf.blit(lbl, (fist[0] - 5, fist[1] - 8))
