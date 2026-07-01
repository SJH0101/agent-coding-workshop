"""
UNIST Boss Game — Stage 4
8개 팔 전투 시스템 (ArmBase 기반), 파티클, 화면흔들림
"""
import pygame
import math
import random

SCREEN_W = 1280
SCREEN_H = 720

# ═══════════════════════════════════════════════════════════════════════════════
# 파티클 시스템 (Stage 2와 동일)
# ═══════════════════════════════════════════════════════════════════════════════

class Particle:
    def __init__(self, x, y, color, lifespan=500):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2.0, 7.0)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.lifespan = lifespan
        self.age = 0.0
        self.size = random.randint(3, 7)
        self.alive = True

    def update(self, dt):
        self.age += dt
        if self.age >= self.lifespan:
            self.alive = False
            return
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96

    def draw(self, surf, offset=(0, 0)):
        if not self.alive:
            return
        alpha = int(255 * max(0.0, 1.0 - self.age / self.lifespan))
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill((*self.color, alpha))
        surf.blit(s, (self.x + offset[0], self.y + offset[1]))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=8, lifespan=500):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, lifespan))

    def update(self, dt):
        alive = [p for p in self.particles if (p.update(dt) or True) and p.alive]
        # Re-check alive after update
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surf, offset=(0, 0)):
        for p in self.particles:
            p.draw(surf, offset)

    def clear(self):
        self.particles.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 화면 흔들림 (Stage 2와 동일)
# ═══════════════════════════════════════════════════════════════════════════════

class ScreenShake:
    def __init__(self):
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.timer = 0.0
        self.intensity = 0.0

    def trigger(self, duration=150, intensity=8.0):
        self.timer = duration
        self.intensity = intensity

    def update(self, dt):
        if self.timer <= 0:
            self.offset_x = 0.0
            self.offset_y = 0.0
            return
        self.timer -= dt
        if self.timer < 0:
            self.timer = 0.0
        factor = (self.timer / 150.0) * self.intensity
        self.offset_x = random.uniform(-factor, factor)
        self.offset_y = random.uniform(-factor, factor)

    def get_offset(self):
        return (int(self.offset_x), int(self.offset_y))


# ═══════════════════════════════════════════════════════════════════════════════
# ArmBase — 모든 팔의 기본 클래스
# ═══════════════════════════════════════════════════════════════════════════════

SHARED_COLORS = {
    'F':         (160, 160, 170),
    'chain':     (120, 200, 120),
    'spear':     (200, 120, 80),
    'hammer':    (200, 180, 60),
    'whip':      (160, 80,  200),
    'shield':    (60,  120, 200),
    'hook':      (200, 100, 100),
    'boomerang': (100, 200, 200),
}

# 팔 고정 위치 (보스 rect 기준 normalized 0~1)
ARM_ANCHORS = [
    ('F',         0.85, 0.15),   # 우상단
    ('chain',     0.15, 0.15),   # 좌상단
    ('spear',     1.05, 0.50),   # 우측
    ('hammer',    0.85, 0.85),   # 우하단
    ('whip',      0.15, 0.85),   # 좌하단
    ('shield',    -0.05, 0.50),  # 좌측
    ('hook',      0.50, -0.10),  # 상단
    ('boomerang', 0.50, 1.10),   # 하단
]

ARM_ORDER = [name for name, *_ in ARM_ANCHORS]


class ArmBase:
    HP_MAX = 1

    # 공통 상태
    STATE_DESTROYED = -1
    STATE_ACTIVE = 0    # 각 팔이 세부 상태를 자유롭게 정의

    def __init__(self, name, boss_rect, hp=3):
        self.name = name
        self.boss_rect = boss_rect
        self.HP_MAX = hp
        self.hp = hp
        self.state = self.STATE_ACTIVE
        self.color = SHARED_COLORS.get(name, (150, 150, 150))
        self.glow = 0.0
        self.hitbox = pygame.Rect(0, 0, 0, 0)   # 플레이어에게 위험한 영역
        self.timer = 0.0
        self.shield_visual = 0.0  # shield arm glow

    # ── 앵커 포인트 ──
    def _get_anchor(self, ox=0, oy=0):
        """보스 rect 기준 앵커 좌표"""
        r = self.boss_rect
        for aname, ax, ay in ARM_ANCHORS:
            if aname == self.name:
                return (r.x + r.w * ax + ox, r.y + r.h * ay + oy)
        return (r.centerx, r.centery)

    # ── 공통: hurtbox (각 팔이 오버라이드 권장) ──
    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        return pygame.Rect(ax - 20, ay - 20, 40, 40)

    # ── 공통: 데미지 ──
    def take_damage(self, amount=1):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.state = self.STATE_DESTROYED
            return True  # 파괴됨
        return False

    # ── 공통: 타격/파괴 이펙트 ──
    def hit_effect(self, gs, x, y):
        gs.particles.emit(x, y, (255, 200, 100), count=8, lifespan=400)
        gs.shake.trigger(duration=120, intensity=9.0)

    def destroy_effect(self, gs, x, y):
        gs.particles.emit(x, y, (255, 200, 50), count=20, lifespan=600)
        gs.particles.emit(x, y, self.color, count=15, lifespan=500)
        gs.shake.trigger(duration=250, intensity=14.0)

    # ── 공통: 텔레그래프 글로우 그리기 ──
    def draw_telegraph(self, surf, cx, cy, radius=35):
        r = max(5, radius + int(self.glow * 12))
        g = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        alpha = max(0, int(70 + self.glow * 80))
        pygame.draw.circle(g, (255, 40, 40, alpha), (r, r), r)
        surf.blit(g, (cx - r, cy - r))

    def update(self, dt, player_rect):
        raise NotImplementedError

    def draw(self, surf):
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════════
# 각 팔 구현
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. F 낫 ───────────────────────────────────────────────────────────────────

class ArmF(ArmBase):
    STATE_IDLE = 0
    STATE_TELEGRAPH = 1
    STATE_SWING = 2
    STATE_RECOVER = 3

    T_IDLE = 3500; T_TELEGRAPH = 800; T_SWING = 400; T_RECOVER = 600

    def __init__(self, boss_rect):
        super().__init__('F', boss_rect, hp=3)
        self.angle = -math.pi / 4
        self.length = 100
        self.swing_target_x = 0
        self.start_angle = -math.pi / 4
        self.end_angle = -math.pi / 4

    def _arm_end(self):
        ax, ay = self._get_anchor()
        ex = ax + math.cos(self.angle) * self.length
        ey = ay + math.sin(self.angle) * self.length
        return (ex, ey)

    def _swing_target_angle(self, px):
        ax, ay = self._get_anchor()
        dx = px - ax
        dy = SCREEN_H * 0.55 - ay
        return math.atan2(dy, dx)

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        sx, sy = self._get_anchor()
        ex, ey = self._arm_end()
        pad = 18
        return pygame.Rect(min(sx, ex) - pad, min(sy, ey) - pad,
                           abs(ex - sx) + pad * 2, abs(ey - sy) + pad * 2)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            t = pygame.time.get_ticks() / 1000.0
            self.angle = -math.pi / 4 + math.sin(t * 1.2) * 0.08
            self.length = 100 + math.sin(t * 0.8) * 4
            self.color = SHARED_COLORS['F']
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                self.swing_target_x = player_rect.centerx
                self.start_angle = self.angle

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            p = self.timer / self.T_TELEGRAPH
            self.glow = math.sin(p * math.pi * 3)
            r = int(150 + 105 * self.glow)
            self.color = (r, 50, 50)
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_SWING
                self.timer = 0.0
                self.end_angle = self._swing_target_angle(self.swing_target_x)

        elif self.state == self.STATE_SWING:
            self.timer += dt
            p = min(self.timer / self.T_SWING, 1.0)
            eased = 1.0 - (1.0 - p) ** 2
            self.angle = self.start_angle + (self.end_angle - self.start_angle) * eased
            self.length = 100 + 80 * eased
            self.color = (255, 60, 60)
            if self.timer >= self.T_SWING:
                self.state = self.STATE_RECOVER
                self.timer = 0.0

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            p = min(self.timer / self.T_RECOVER, 1.0)
            self.angle = self.end_angle + (-math.pi / 4 - self.end_angle) * p
            self.length = 180 - 80 * p
            self.color = (100, 100, 110)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

        ex, ey = self._arm_end()
        bs = 24
        if self.state == self.STATE_SWING:
            self.hitbox = pygame.Rect(ex - bs//2, ey - bs//2, bs, bs)
        else:
            self.hitbox = pygame.Rect(0, 0, 0, 0)

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()
        ex, ey = self._arm_end()

        if self.state == self.STATE_TELEGRAPH:
            self.draw_telegraph(surf, ex, ey)

        # 팔
        arm_w = 10
        dx, dy = ex - ax, ey - ay
        dist = math.hypot(dx, dy)
        if dist > 0:
            nx, ny = -dy/dist * arm_w/2, dx/dist * arm_w/2
            pts = [(ax+nx, ay+ny), (ex+nx, ey+ny), (ex-nx, ey-ny), (ax-nx, ay-ny)]
            pygame.draw.polygon(surf, self.color, pts)
            pygame.draw.polygon(surf, tuple(min(255,c+40) for c in self.color), pts, 2)

        # 낫 끝
        tri_sz = 22
        pa = self.angle + math.pi/2
        tip = (ex + math.cos(self.angle)*14, ey + math.sin(self.angle)*14)
        l = (ex + math.cos(pa-0.3)*tri_sz, ey + math.sin(pa-0.3)*tri_sz)
        r = (ex + math.cos(pa+0.3)*tri_sz, ey + math.sin(pa+0.3)*tri_sz)
        pygame.draw.polygon(surf, (200,200,210), [tip, l, r])
        pygame.draw.polygon(surf, (160,160,170), [tip, l, r], 2)


# ── 2. 재수강 사슬 ────────────────────────────────────────────────────────────

class ArmChain(ArmBase):
    STATE_IDLE = 0; STATE_TELEGRAPH = 1; STATE_THROW = 2; STATE_RECOVER = 3
    T_IDLE = 2800; T_TELEGRAPH = 700; T_THROW = 400; T_RECOVER = 500

    def __init__(self, boss_rect):
        super().__init__('chain', boss_rect, hp=2)
        self.chain_progress = 0.0  # 0~1
        self.max_reach = 450
        self.target_x = 0
        self.target_y = 0
        self.chain_pos = (0, 0)

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        cx, cy = self.chain_pos
        pad = 15
        return pygame.Rect(min(ax, cx) - pad, min(ay, cy) - pad,
                           abs(cx - ax) + pad*2, abs(cy - ay) + pad*2)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            self.color = SHARED_COLORS['chain']
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                self.target_x = player_rect.centerx
                self.target_y = player_rect.centery

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            p = self.timer / self.T_TELEGRAPH
            self.glow = math.sin(p * math.pi * 3)
            self.color = (100 + int(100 * self.glow), 200, 100)
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_THROW
                self.timer = 0.0
                self.chain_progress = 0.0

        elif self.state == self.STATE_THROW:
            self.timer += dt
            self.chain_progress = min(self.timer / self.T_THROW, 1.0)
            eased = 1.0 - (1.0 - self.chain_progress) ** 2
            self.chain_pos = (
                ax + (self.target_x - ax) * eased,
                ay + (self.target_y - ay) * eased
            )
            # hitbox during throw
            cx, cy = self.chain_pos
            self.hitbox = pygame.Rect(cx - 15, cy - 15, 30, 30)
            self.color = (100, 220, 120)
            if self.timer >= self.T_THROW:
                self.state = self.STATE_RECOVER
                self.timer = 0.0

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            p = min(self.timer / self.T_RECOVER, 1.0)
            # chain returns
            self.chain_pos = (
                self.target_x + (ax - self.target_x) * p,
                self.target_y + (ay - self.target_y) * p
            )
            self.hitbox = pygame.Rect(0, 0, 0, 0)
            self.color = (80, 160, 80)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()
        cx, cy = self.chain_pos

        if self.state == self.STATE_TELEGRAPH:
            self.draw_telegraph(surf, ax, ay - 30)

        # 사슬
        if self.state in (self.STATE_THROW, self.STATE_RECOVER):
            # 체인 링크
            dx, dy = cx - ax, cy - ay
            dist = math.hypot(dx, dy)
            if dist > 0:
                links = max(3, int(dist / 20))
                for i in range(links + 1):
                    t = i / links
                    lx = ax + dx * t
                    ly = ay + dy * t
                    sz = 6 if i % 2 == 0 else 4
                    pygame.draw.circle(surf, (150, 220, 150), (int(lx), int(ly)), sz)
                    pygame.draw.circle(surf, self.color, (int(lx), int(ly)), sz, 1)
            # 끝 갈고리
            pygame.draw.circle(surf, (200, 255, 200), (int(cx), int(cy)), 10)
            pygame.draw.circle(surf, self.color, (int(cx), int(cy)), 10, 2)

        # 앵커 마커
        pygame.draw.circle(surf, self.color, (int(ax), int(ay)), 12)
        pygame.draw.circle(surf, (255, 255, 255), (int(ax), int(ay)), 12, 2)

    def on_hit_player(self, player):
        """플레이어를 시작 지점으로 텔레포트"""
        player.rect.x = 600
        player.rect.y = SCREEN_H - 120
        player.vy = 0
        player.vx = 0


# ── 3. D+ 창 ──────────────────────────────────────────────────────────────────

class ArmSpear(ArmBase):
    STATE_IDLE = 0; STATE_TELEGRAPH = 1; STATE_THRUST = 2; STATE_RECOVER = 3
    T_IDLE = 2000; T_TELEGRAPH = 500; T_THRUST = 250; T_RECOVER = 500

    def __init__(self, boss_rect):
        super().__init__('spear', boss_rect, hp=2)
        self.thrust_progress = 0.0
        self.thrust_x = 0
        self.thrust_y = 0

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        tx, ty = self.thrust_x, self.thrust_y
        pad = 12
        return pygame.Rect(min(ax, tx) - pad, min(ay, ty) - pad,
                           abs(tx - ax) + pad*2, abs(ty - ay) + pad*2)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            self.color = SHARED_COLORS['spear']
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                self.thrust_x = player_rect.centerx
                self.thrust_y = player_rect.centery

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            self.glow = math.sin(self.timer / self.T_TELEGRAPH * math.pi * 3)
            self.color = (220, 120 + int(80 * self.glow), 60)
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_THRUST
                self.timer = 0.0

        elif self.state == self.STATE_THRUST:
            self.timer += dt
            self.thrust_progress = min(self.timer / self.T_THRUST, 1.0)
            # 찌르기 끝점
            eased = self.thrust_progress ** 0.5  # fast initial
            self.thrust_x = ax + (self.thrust_x - ax) * eased
            self.thrust_y = ay + (self.thrust_y - ay) * eased
            # hitbox
            self.hitbox = pygame.Rect(self.thrust_x - 10, self.thrust_y - 10, 20, 20)
            self.color = (240, 160, 80)
            if self.timer >= self.T_THRUST:
                self.state = self.STATE_RECOVER
                self.timer = 0.0

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            p = min(self.timer / self.T_RECOVER, 1.0)
            self.thrust_x = self.thrust_x + (ax - self.thrust_x) * p
            self.thrust_y = self.thrust_y + (ay - self.thrust_y) * p
            self.hitbox = pygame.Rect(0, 0, 0, 0)
            self.color = (160, 100, 60)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()
        tx, ty = self.thrust_x, self.thrust_y

        if self.state == self.STATE_TELEGRAPH:
            self.draw_telegraph(surf, ax + (tx - ax) * 0.5, ay + (ty - ay) * 0.5)

        # 창대
        if self.state in (self.STATE_THRUST, self.STATE_RECOVER):
            pygame.draw.line(surf, (140, 90, 50), (ax, ay), (tx, ty), 6)
            # 창끝
            ang = math.atan2(ty - ay, tx - ax)
            tip = (tx + math.cos(ang) * 16, ty + math.sin(ang) * 16)
            l = (tx + math.cos(ang + 2.3) * 14, ty + math.sin(ang + 2.3) * 14)
            r = (tx + math.cos(ang - 2.3) * 14, ty + math.sin(ang - 2.3) * 14)
            pygame.draw.polygon(surf, (220, 180, 140), [tip, l, r])
            pygame.draw.polygon(surf, self.color, [tip, l, r], 2)
        else:
            pygame.draw.line(surf, self.color, (ax, ay), (ax + 10, ay + 10), 4)


# ── 4. 출석 도장 망치 ────────────────────────────────────────────────────────

class ArmHammer(ArmBase):
    STATE_IDLE = 0; STATE_TELEGRAPH = 1; STATE_SMASH = 2; STATE_RECOVER = 3
    T_IDLE = 3000; T_TELEGRAPH = 1000; T_SMASH = 450; T_RECOVER = 700

    def __init__(self, boss_rect):
        super().__init__('hammer', boss_rect, hp=3)
        self.smash_x = 0
        self.smash_progress = 0.0
        self.hammer_y = 0
        self.impact_y = 0

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        return pygame.Rect(ax - 22, ay - 22, 44, 44)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            self.color = SHARED_COLORS['hammer']
            self.hammer_y = ay - 30 + math.sin(pygame.time.get_ticks() / 300) * 5
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                self.smash_x = player_rect.centerx
                self.impact_y = SCREEN_H - 60  # 바닥

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            p = self.timer / self.T_TELEGRAPH
            self.glow = max(0, math.sin(p * math.pi * 2))
            r = int(120 + 135 * self.glow)
            self.color = (r, 180, 60)
            # 바닥에 예고 표시
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_SMASH
                self.timer = 0.0
                self.smash_progress = 0.0

        elif self.state == self.STATE_SMASH:
            self.timer += dt
            self.smash_progress = min(self.timer / self.T_SMASH, 1.0)
            # 망치가 위에서 아래로
            eased = self.smash_progress ** 2
            self.hammer_y = ay - 80 + (self.impact_y - (ay - 80)) * eased
            p = self.smash_progress
            self.color = (255, 200 - int(100 * p), 50)
            # 충돌 박스 (착지 순간)
            if p >= 0.7:
                w = 160 * (p - 0.7) * 3.3  # 점점 확장
                self.hitbox = pygame.Rect(ax - w//2, self.impact_y - 60, w, 60)
            else:
                self.hitbox = pygame.Rect(0, 0, 0, 0)
            if self.timer >= self.T_SMASH:
                self.state = self.STATE_RECOVER
                self.timer = 0.0

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            p = min(self.timer / self.T_RECOVER, 1.0)
            self.hammer_y = self.impact_y - (self.impact_y - (ay - 80)) * p
            self.hitbox = pygame.Rect(0, 0, 0, 0)
            self.color = (180 - int(60 * p), 160 - int(40 * p), 60)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        # 예고 영역
        if self.state == self.STATE_TELEGRAPH:
            w = 160 + int(self.glow * 20)
            for r in range(int(w), 0, -20):
                alpha = max(20, int(60 * (1 - r/w) * self.glow))
                s = pygame.Surface((r, 60), pygame.SRCALPHA)
                s.fill((255, 100, 50, alpha))
                surf.blit(s, (ax - r // 2, SCREEN_H - 60))
            self.draw_telegraph(surf, ax, ay - 60)

        # 망치 머리
        hx, hy = ax, self.hammer_y
        mx, my = ax, ay
        # 손잡이
        pygame.draw.line(surf, (100, 70, 30), (mx, my), (hx, hy), 6)
        # 망치 머리
        if self.state == self.STATE_ACTIVE or self.state == self.STATE_IDLE:
            pygame.draw.rect(surf, self.color, (hx - 20, hy - 12, 40, 24), border_radius=4)
            pygame.draw.rect(surf, (255, 255, 200), (hx - 20, hy - 12, 40, 24), 2, border_radius=4)
        else:
            sz = 24 + int(16 * self.smash_progress if hasattr(self, 'smash_progress') else 0)
            pygame.draw.rect(surf, self.color, (hx - sz//2, hy - 10, sz, 20), border_radius=3)
            pygame.draw.rect(surf, (255, 200, 100), (hx - sz//2, hy - 10, sz, 20), 2, border_radius=3)

        # 충돌 이펙트 (바닥 충돌 시)
        if self.state == self.STATE_SMASH and self.smash_progress >= 0.7:
            w = 160 * (self.smash_progress - 0.7) * 3.3
            alpha = int(150 * (1 - (self.smash_progress - 0.7) / 0.3))
            s = pygame.Surface((w, 40), pygame.SRCALPHA)
            s.fill((255, 180, 50, alpha))
            surf.blit(s, (hx - w // 2, self.impact_y - 20))


# ── 5. 레퍼런스 부족 채찍 ────────────────────────────────────────────────────

class ArmWhip(ArmBase):
    STATE_IDLE = 0; STATE_TELEGRAPH = 1; STATE_LASH = 2; STATE_RECOVER = 3
    T_IDLE = 2500; T_TELEGRAPH = 600; T_LASH = 350; T_RECOVER = 700
    MAX_REACH = 600
    CC_DURATION = 500  # ms

    def __init__(self, boss_rect):
        super().__init__('whip', boss_rect, hp=2)
        self.lash_progress = 0.0
        self.target_x = 0
        self.target_y = 0
        self.lash_end = (0, 0)
        self.curve_pts = []

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        return pygame.Rect(ax - 15, ay - 15, 30, 30)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            self.color = SHARED_COLORS['whip']
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                dx = player_rect.centerx - ax
                dy = player_rect.centery - ay
                dist = math.hypot(dx, dy)
                limited = min(dist, self.MAX_REACH)
                self.target_x = ax + dx / dist * limited
                self.target_y = ay + dy / dist * limited

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            self.glow = math.sin(self.timer / self.T_TELEGRAPH * math.pi * 3)
            self.color = (160 + int(80 * self.glow), 80, 200)
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_LASH
                self.timer = 0.0
                self.lash_progress = 0.0

        elif self.state == self.STATE_LASH:
            self.timer += dt
            self.lash_progress = min(self.timer / self.T_LASH, 1.0)
            eased = self.lash_progress ** 0.7
            cx = ax + (self.target_x - ax) * eased
            cy = ay + (self.target_y - ay) * eased
            self.lash_end = (cx, cy)
            # 채찍 곡선
            mid_x = (ax + cx) / 2
            mid_y = min(ay, cy) - 40 + math.sin(eased * math.pi) * 80
            self.curve_pts = [
                (ax, ay),
                ((ax + mid_x)/2, (ay + mid_y)/2 - 20),
                (mid_x, mid_y),
                ((mid_x + cx)/2, (mid_y + cy)/2 - 10),
                (cx, cy),
            ]
            # 얇은 hitbox
            self.hitbox = pygame.Rect(cx - 8, cy - 8, 16, 16)
            self.color = (200, 100, 240)
            if self.timer >= self.T_LASH:
                self.state = self.STATE_RECOVER
                self.timer = 0.0

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            p = min(self.timer / self.T_RECOVER, 1.0)
            self.lash_end = (self.target_x + (ax - self.target_x) * p,
                             self.target_y + (ay - self.target_y) * p)
            self.hitbox = pygame.Rect(0, 0, 0, 0)
            self.color = (120, 60, 160)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_TELEGRAPH:
            self.draw_telegraph(surf, ax + (self.target_x - ax) * 0.3,
                                ay + (self.target_y - ay) * 0.3)

        # 채찍
        if self.state in (self.STATE_LASH, self.STATE_RECOVER) and self.curve_pts:
            for i in range(len(self.curve_pts) - 1):
                w = max(1, 5 - i)
                pygame.draw.line(surf, self.color,
                                 self.curve_pts[i], self.curve_pts[i+1], w)
                pygame.draw.line(surf, (255, 200, 255),
                                 self.curve_pts[i], self.curve_pts[i+1], 1)
        else:
            pygame.draw.line(surf, self.color, (ax, ay), (ax + 8, ay + 15), 4)


# ── 6. 결석 사유서 방패팔 ─────────────────────────────────────────────────────

class ArmShield(ArmBase):
    def __init__(self, boss_rect):
        super().__init__('shield', boss_rect, hp=5)
        self.shield_radius = 30

    def take_damage(self, amount=1):
        # 방패는 Boss.can_damage_shield()에서 이미 검사하므로
        # 여기서는 그냥 부모 호출
        return super().take_damage(amount)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        self.shield_visual = (pygame.time.get_ticks() / 1000.0)
        self.color = SHARED_COLORS['shield']
        self.hitbox = pygame.Rect(0, 0, 0, 0)  # 공격 안 함

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()
        pulse = 1.0 + math.sin(self.shield_visual * 2) * 0.08

        # 방패 시각 효과
        r = int(self.shield_radius * pulse)
        alpha = int(80 + 40 * math.sin(self.shield_visual * 2))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (50, 100, 200, alpha), (r, r), r)
        pygame.draw.circle(s, (80, 150, 255, alpha + 40), (r, r), r, 3)
        surf.blit(s, (ax - r, ay - r))

        # 방패 아이콘
        pygame.draw.rect(surf, (60, 120, 200),
                         (ax - 18, ay - 22, 36, 44), border_radius=6)
        pygame.draw.rect(surf, (100, 180, 255),
                         (ax - 18, ay - 22, 36, 44), 3, border_radius=6)
        # 방패 문양
        pygame.draw.line(surf, (150, 220, 255), (ax - 8, ay), (ax, ay + 12), 3)
        pygame.draw.line(surf, (150, 220, 255), (ax, ay + 12), (ax + 8, ay), 3)


# ── 7. 팀플 무임승차 갈고리 ───────────────────────────────────────────────────

class ArmHook(ArmBase):
    STATE_IDLE = 0; STATE_TELEGRAPH = 1; STATE_FIRE = 2; STATE_RECOVER = 3
    T_IDLE = 2800; T_TELEGRAPH = 500; T_FLIGHT = 600; T_RECOVER = 400

    def __init__(self, boss_rect):
        super().__init__('hook', boss_rect, hp=2)
        self.hook_x = 0
        self.hook_y = 0
        self.target_x = 0
        self.target_y = 0
        self.flight_progress = 0.0
        self.returning = False  # False=전진, True=회수

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        return pygame.Rect(ax - 15, ay - 15, 30, 30)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            self.color = SHARED_COLORS['hook']
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                self.target_x = player_rect.centerx
                self.target_y = player_rect.centery

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            self.glow = math.sin(self.timer / self.T_TELEGRAPH * math.pi * 3)
            self.color = (200, 100 + int(80 * self.glow), 100)
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_FIRE
                self.timer = 0.0
                self.flight_progress = 0.0
                self.returning = False
                self.hook_x = ax
                self.hook_y = ay

        elif self.state == self.STATE_FIRE:
            self.timer += dt
            self.flight_progress = min(self.timer / self.T_FLIGHT, 1.0)
            if not self.returning:
                # 전진
                eased = 1.0 - (1.0 - self.flight_progress) ** 2
                self.hook_x = ax + (self.target_x - ax) * eased
                self.hook_y = ay + (self.target_y - ay) * eased
                self.hitbox = pygame.Rect(self.hook_x - 12, self.hook_y - 12, 24, 24)
                # 끝까지 도달하면 회수
                if self.flight_progress >= 0.95:
                    self.returning = True
                    self.timer = 0.0
            else:
                # 회수
                p = self.flight_progress
                self.hook_x = self.hook_x + (ax - self.hook_x) * 0.08
                self.hook_y = self.hook_y + (ay - self.hook_y) * 0.08
                self.hitbox = pygame.Rect(self.hook_x - 12, self.hook_y - 12, 24, 24)
                # 가까워지면 상태 종료
                dist = math.hypot(self.hook_x - ax, self.hook_y - ay)
                if dist < 30 or self.timer > 800:
                    self.state = self.STATE_RECOVER
                    self.timer = 0.0

            self.color = (220, 120, 120)

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            p = min(self.timer / self.T_RECOVER, 1.0)
            self.hook_x = ax + (self.hook_x - ax) * (1 - p)
            self.hook_y = ay + (self.hook_y - ay) * (1 - p)
            self.hitbox = pygame.Rect(0, 0, 0, 0)
            self.color = (160, 80, 80)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_TELEGRAPH:
            self.draw_telegraph(surf, ax + (self.target_x - ax) * 0.3,
                                ay + (self.target_y - ay) * 0.3)

        # 줄
        if self.state in (self.STATE_FIRE, self.STATE_RECOVER):
            pygame.draw.line(surf, (120, 60, 60), (ax, ay), (self.hook_x, self.hook_y), 3)
            # 갈고리
            cx, cy = int(self.hook_x), int(self.hook_y)
            pygame.draw.circle(surf, (180, 100, 100), (cx, cy), 10)
            pygame.draw.circle(surf, (255, 200, 200), (cx, cy), 10, 2)
            # 갈고리 끝
            for ang_offset in [-0.5, 0.5]:
                ang = math.atan2(cy - ay, cx - ax) + ang_offset
                tip_x = cx + math.cos(ang) * 14
                tip_y = cy + math.sin(ang) * 14
                pygame.draw.line(surf, (180, 100, 100), (cx, cy), (tip_x, tip_y), 3)
        else:
            pygame.draw.circle(surf, self.color, (int(ax), int(ay)), 10)
            pygame.draw.circle(surf, (255, 200, 200), (int(ax), int(ay)), 10, 2)

    def on_hit_player(self, player):
        """플레이어를 보스 쪽으로 끌어당김"""
        ax, ay = self._get_anchor()
        dx = ax - player.rect.centerx
        dy = ay - player.rect.centery - 80
        dist = math.hypot(dx, dy)
        if dist > 0:
            pull_strength = 15
            player.rect.x += dx / dist * pull_strength
            player.rect.y += dy / dist * pull_strength
            player.vy = dy / dist * 5
        player.climbing = False


# ── 8. 디펜스 압박 부메랑 ─────────────────────────────────────────────────────

class ArmBoomerang(ArmBase):
    STATE_IDLE = 0; STATE_TELEGRAPH = 1; STATE_THROW = 2; STATE_RETURN = 3; STATE_RECOVER = 4
    T_IDLE = 3000; T_TELEGRAPH = 700; T_THROW = 700; T_RETURN = 700; T_RECOVER = 300

    def __init__(self, boss_rect):
        super().__init__('boomerang', boss_rect, hp=3)
        self.boomerang_x = 0.0
        self.boomerang_y = 0.0
        self.boomerang_angle = 0.0
        self.arc_offset = 0.0
        self.throw_progress = 0.0
        self.return_progress = 0.0
        self.target_x = 0
        self.target_y = 0

    def get_hurtbox(self):
        if self.state == self.STATE_DESTROYED:
            return pygame.Rect(0, 0, 0, 0)
        ax, ay = self._get_anchor()
        return pygame.Rect(ax - 18, ay - 18, 36, 36)

    def update(self, dt, player_rect):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_IDLE:
            self.timer += dt
            self.color = SHARED_COLORS['boomerang']
            if self.timer >= self.T_IDLE:
                self.state = self.STATE_TELEGRAPH
                self.timer = 0.0
                self.target_x = player_rect.centerx
                self.target_y = player_rect.centery

        elif self.state == self.STATE_TELEGRAPH:
            self.timer += dt
            self.glow = math.sin(self.timer / self.T_TELEGRAPH * math.pi * 3)
            self.color = (100 + int(80 * self.glow), 200, 200)
            if self.timer >= self.T_TELEGRAPH:
                self.state = self.STATE_THROW
                self.timer = 0.0
                self.throw_progress = 0.0
                self.boomerang_x = ax
                self.boomerang_y = ay

        elif self.state == self.STATE_THROW:
            self.timer += dt
            self.throw_progress = min(self.timer / self.T_THROW, 1.0)
            eased = 1.0 - (1.0 - self.throw_progress) ** 2
            # 포물선: 전진 + 위아래 호
            p = eased
            cx = ax + (self.target_x - ax) * p
            cy = ay + (self.target_y - ay) * p
            arc = math.sin(p * math.pi) * 80
            self.boomerang_x = cx + math.sin(p * math.pi * 2) * 30
            self.boomerang_y = cy + arc
            self.boomerang_angle += 0.2
            self.hitbox = pygame.Rect(self.boomerang_x - 18, self.boomerang_y - 18, 36, 36)
            self.color = (120, 220, 220)
            if self.timer >= self.T_THROW:
                self.state = self.STATE_RETURN
                self.timer = 0.0
                self.return_progress = 0.0

        elif self.state == self.STATE_RETURN:
            self.timer += dt
            self.return_progress = min(self.timer / self.T_RETURN, 1.0)
            p = self.return_progress
            # 돌아오기 (포물선 반대)
            start_x = self.boomerang_x
            start_y = self.boomerang_y
            end_x = ax + (ax - self.target_x) * 0.3  # 약간 반대쪽으로 돌아옴
            end_y = ay - 40
            self.boomerang_x = start_x + (end_x - start_x) * p
            self.boomerang_y = start_y + (end_y - start_y) * p + math.sin(p * math.pi) * 40
            self.boomerang_angle += 0.25
            self.hitbox = pygame.Rect(self.boomerang_x - 18, self.boomerang_y - 18, 36, 36)
            self.color = (150, 200, 200)
            dist = math.hypot(self.boomerang_x - ax, self.boomerang_y - ay)
            if dist < 40 or self.timer > 1000:
                self.state = self.STATE_RECOVER
                self.timer = 0.0

        elif self.state == self.STATE_RECOVER:
            self.timer += dt
            self.boomerang_x += (ax - self.boomerang_x) * 0.1
            self.boomerang_y += (ay - self.boomerang_y) * 0.1
            self.hitbox = pygame.Rect(0, 0, 0, 0)
            self.color = (80, 160, 160)
            if self.timer >= self.T_RECOVER:
                self.state = self.STATE_IDLE
                self.timer = 0.0

    def draw(self, surf):
        if self.state == self.STATE_DESTROYED:
            return
        ax, ay = self._get_anchor()

        if self.state == self.STATE_TELEGRAPH:
            self.draw_telegraph(surf, ax + (self.target_x - ax) * 0.3,
                                ay + (self.target_y - ay) * 0.3)

        if self.state in (self.STATE_THROW, self.STATE_RETURN):
            bx, by = int(self.boomerang_x), int(self.boomerang_y)
            # 부메랑 모양
            pts = []
            for i in range(8):
                a = math.pi * 2 * i / 8 + self.boomerang_angle
                r = 18 if i % 2 == 0 else 8
                pts.append((bx + math.cos(a) * r, by + math.sin(a) * r))
            pygame.draw.polygon(surf, self.color, pts)
            pygame.draw.polygon(surf, (200, 255, 255), pts, 2)
            # 회전 궤적 (흔적)
            if self.state == self.STATE_THROW:
                alpha = int(60 * (1 - self.throw_progress))
                s = pygame.Surface((50, 50), pygame.SRCALPHA)
                pygame.draw.circle(s, (100, 200, 200, alpha), (25, 25), 22)
                surf.blit(s, (bx - 25, by - 25))
        else:
            # 대기 시 앵커 마커
            pts = []
            for i in range(8):
                a = math.pi * 2 * i / 8
                r = 14 if i % 2 == 0 else 6
                pts.append((ax + math.cos(a) * r, ay + math.sin(a) * r))
            pygame.draw.polygon(surf, self.color, pts)
            pygame.draw.polygon(surf, (180, 230, 230), pts, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 보스
# ═══════════════════════════════════════════════════════════════════════════════

ARM_CLASSES = {
    'F': ArmF, 'chain': ArmChain, 'spear': ArmSpear,
    'hammer': ArmHammer, 'whip': ArmWhip, 'shield': ArmShield,
    'hook': ArmHook, 'boomerang': ArmBoomerang,
}


class Boss:
    def __init__(self):
        self.rect = pygame.Rect(SCREEN_W // 2 - 100, 40, 200, 120)
        self.color = (90, 90, 110)
        self.border_color = (60, 60, 80)
        self.max_hp = 10
        self.hp = self.max_hp
        self.defeated = False

        # 8개 팔 생성
        self.arms = []
        for name, *_ in ARM_ANCHORS:
            cls = ARM_CLASSES.get(name)
            if cls:
                self.arms.append(cls(self.rect))

    # ── 방패 로직 ──
    def get_shield_arm(self):
        for arm in self.arms:
            if isinstance(arm, ArmShield):
                return arm
        return None

    def is_shield_active(self):
        """방패팔이 살아있고, 다른 팔 중 하나라도 살아있으면 shield active"""
        shield = self.get_shield_arm()
        if shield is None or shield.state == ArmBase.STATE_DESTROYED:
            return False
        for arm in self.arms:
            if isinstance(arm, ArmShield):
                continue
            if arm.state != ArmBase.STATE_DESTROYED:
                return True  # 다른 팔이 아직 살아있음
        return False  # 모든 다른 팔이 파괴됨

    def can_damage_arm(self, arm):
        """방패 로직: shield arm은 다른 팔이 전부 파괴된 후에만 데미지 가능"""
        if isinstance(arm, ArmShield):
            return not self.is_shield_active()  # shield active면 데미지 불가
        return True

    def is_body_vulnerable(self):
        return not self.is_shield_active() and self.hp > 0

    # ── 업데이트 ──
    def update(self, dt, player_rect):
        for arm in self.arms:
            arm.update(dt, player_rect)

    # ── 그리기 ──
    def draw(self, surf):
        r = self.rect
        cx, cy = r.centerx, r.centery
        shielded = self.is_shield_active()

        # 보스 바디 컬러
        body_color = (50, 50, 70) if shielded else (70, 70, 95)

        # === 로브/가운 ===
        # 가운 몸통
        robe_pts = [
            (cx - 60, r.top + 20),
            (cx + 60, r.top + 20),
            (cx + 75, r.bottom - 10),
            (cx - 75, r.bottom - 10),
        ]
        robe_color = (35, 30, 50) if shielded else (45, 35, 60)
        pygame.draw.polygon(surf, robe_color, robe_pts)
        pygame.draw.polygon(surf, (60, 50, 80), robe_pts, 2)
        # 가운 중앙선
        pygame.draw.line(surf, (70, 60, 90), (cx, r.top + 25), (cx, r.bottom - 10), 2)

        # === 얼굴 ===
        face_y = r.top + 15
        face_r = 28
        if shielded:
            face_col = (80, 70, 60)
        else:
            face_col = (150, 130, 110)
        pygame.draw.circle(surf, face_col, (cx, face_y), face_r)
        # 얼굴 테두리
        pygame.draw.circle(surf, (100, 80, 60), (cx, face_y), face_r, 2)

        # === 학위 모자 (graduation cap) ===
        cap_y = face_y - face_r - 2
        # 모자 판
        pygame.draw.rect(surf, (25, 20, 40), (cx - 30, cap_y, 60, 8), border_radius=2)
        # 중앙 술
        tassel = pygame.time.get_ticks() / 500
        tassel_swing = math.sin(tassel) * 3
        pygame.draw.line(surf, (200, 180, 50), (cx + tassel_swing, cap_y),
                         (cx + 5 + tassel_swing, cap_y - 16), 2)
        pygame.draw.circle(surf, (200, 180, 50), (cx + 5 + tassel_swing, cap_y - 16), 3)

        # === 눈 (붉은 glow) ===
        eye_y = face_y - 3
        glow_t = math.sin(pygame.time.get_ticks() / 400) * 0.4 + 0.6
        for ex in (-8, 8):
            # 눈 glow
            gr = int(10 + glow_t * 8)
            g = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            alpha = int(60 + glow_t * 80)
            pygame.draw.circle(g, (255, 30, 30, alpha), (gr, gr), gr)
            surf.blit(g, (cx + ex - gr, eye_y - gr))
            # 눈동자
            pygame.draw.circle(surf, (255, 50, 50), (cx + ex, eye_y), 5)
            pygame.draw.circle(surf, (200, 20, 20), (cx + ex, eye_y), 5, 2)
            # 홍채
            pygame.draw.circle(surf, (255, 200, 100), (cx + ex + 2, eye_y - 1), 2)

        # === 입 ===
        if shielded:
            pygame.draw.arc(surf, (60, 50, 50), (cx - 8, eye_y + 14, 16, 10), 0, math.pi, 2)
        else:
            pygame.draw.arc(surf, (80, 60, 60), (cx - 10, eye_y + 12, 20, 12), 0.2, math.pi - 0.2, 3)

        # === 안경 (교수님) ===
        glass_color = (150, 150, 180)
        pygame.draw.rect(surf, glass_color, (cx - 18, eye_y - 6, 14, 12), 2, border_radius=3)
        pygame.draw.rect(surf, glass_color, (cx + 4, eye_y - 6, 14, 12), 2, border_radius=3)
        pygame.draw.line(surf, glass_color, (cx - 4, eye_y), (cx + 4, eye_y), 2)

        # === 팔 그리기 (보스 본체 위에) ===
        for arm in self.arms:
            arm.draw(surf)

        # === HP bar ===
        bar_w = 220
        bar_h = 18
        bar_x = cx - bar_w // 2
        bar_y = r.top - 44

        bar_bg = (25, 25, 35) if not shielded else (20, 20, 45)
        pygame.draw.rect(surf, bar_bg, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        if self.hp > 0 and not shielded:
            fill = int(bar_w * (self.hp / self.max_hp))
            hp_color = (220, 60, 60) if self.hp <= 3 else (200, 50, 50)
            pygame.draw.rect(surf, hp_color, (bar_x + 2, bar_y + 2, fill - 4, bar_h - 4), border_radius=3)
        pygame.draw.rect(surf, (100, 100, 120), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)

        # HP bar 텍스트
        try:
            f = pygame.font.SysFont("AppleGothic", 12)
        except:
            f = pygame.font.Font(None, 12)
        hp_text = f.render(f"PROFESSOR", True, (200, 200, 220))
        surf.blit(hp_text, (bar_x + 5, bar_y - 16))

        # 무적 표시
        if shielded:
            lx, ly = bar_x + bar_w + 10, bar_y + 2
            # 방패 아이콘
            pygame.draw.polygon(surf, (80, 140, 255), [
                (lx + 7, ly), (lx + 14, ly + 6), (lx + 14, ly + 12),
                (lx + 7, ly + 16), (lx, ly + 12), (lx, ly + 6)])
            pygame.draw.polygon(surf, (150, 200, 255), [
                (lx + 7, ly), (lx + 14, ly + 6), (lx + 14, ly + 12),
                (lx + 7, ly + 16), (lx, ly + 12), (lx, ly + 6)], 2)