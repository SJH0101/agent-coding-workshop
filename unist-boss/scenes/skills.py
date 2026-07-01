"""
UNIST Boss Game — Stage 3
스킬 시스템 (메이플스토리 스타일)
"""
import pygame
import math
import random

# ── 화면 상수 ──
SCREEN_W = 1280
SCREEN_H = 720


# ═══════════════════════════════════════════════════════════════════════════════
# 스킬 발사체/이펙트
# ═══════════════════════════════════════════════════════════════════════════════

class SkillProjectile:
    """스킬 사용 시 생성되는 발사체 또는 이펙트 객체"""

    def __init__(self, x, y, vx, vy, color, size=20, lifespan=600, damage=1,
                 effect_type='projectile', shape='rect', owner='player'):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.size = size
        self.lifespan = lifespan  # ms
        self.age = 0.0
        self.damage = damage
        self.effect_type = effect_type
        self.shape = shape  # 'rect', 'circle', 'star', 'slash'
        self.owner = owner
        self.alive = True
        self.hit_targets = set()  # 이미 맞은 대상 id

        # hitbox
        self.hitbox = pygame.Rect(0, 0, size, size)
        self.hitbox.center = (int(x), int(y))

        # 추가 속성
        self.angle = math.atan2(vy, vx)
        self.scale = 1.0
        self.rotation = 0.0

    def update(self, dt, platforms=None):
        self.age += dt
        if self.age >= self.lifespan:
            self.alive = False
            return

        self.x += self.vx
        self.y += self.vy
        self.rotation += dt * 0.1

        # 발사체 감속
        if self.effect_type == 'projectile':
            self.vx *= 0.98

        # 플랫폼 충돌
        if platforms:
            test_rect = pygame.Rect(0, 0, self.size, self.size)
            test_rect.center = (int(self.x), int(self.y))
            for plat in platforms:
                if test_rect.colliderect(plat):
                    self.alive = False
                    return

        # hitbox 갱신
        self.hitbox.center = (int(self.x), int(self.y))

        # 스케일 페이드
        self.scale = max(0.3, 1.0 - (self.age / self.lifespan) * 0.5)

    def draw(self, surf):
        if not self.alive:
            return

        alpha = int(255 * max(0.2, 1.0 - self.age / self.lifespan))
        size = int(self.size * self.scale)
        cx, cy = int(self.x), int(self.y)

        if self.shape == 'rect':
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surf.blit(s, s.get_rect(center=(cx, cy)))

        elif self.shape == 'circle':
            pygame.draw.circle(surf, (*self.color, alpha), (cx, cy), size // 2)

        elif self.shape == 'star':
            pts = []
            for i in range(10):
                a = math.pi * 2 * i / 10 - math.pi / 2 + self.rotation
                r = size // 2 if i % 2 == 0 else size // 4
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
            pygame.draw.polygon(surf, (*self.color, alpha), pts, 2)

        elif self.shape == 'slash':
            # 참격 이펙트 (호)
            for i in range(3):
                a = self.angle + math.radians(-30 + i * 30) + self.rotation * 0.5
                dist = size * (0.5 + i * 0.25)
                ex = cx + math.cos(a) * dist
                ey = cy + math.sin(a) * dist
                thickness = max(1, 3 - i)
                fade_alpha = int(alpha * (1.0 - i * 0.25))
                pygame.draw.line(surf, (*self.color, fade_alpha),
                                 (cx, cy), (ex, ey), thickness)

    def has_hit(self, target_id):
        if target_id in self.hit_targets:
            return True
        self.hit_targets.add(target_id)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# 스킬 정의
# ═══════════════════════════════════════════════════════════════════════════════

class Skill:
    def __init__(self, name, key_label, pygame_key, max_cooldown, color,
                 description, skill_type='projectile', damage=1):
        self.name = name
        self.key_label = key_label
        self.pygame_key = pygame_key
        self.max_cooldown = max_cooldown  # ms
        self.current_cooldown = 0.0
        self.color = color
        self.description = description
        self.skill_type = skill_type
        self.damage = damage
        self.buff_timer = 0.0
        self.buff_duration = 0.0

    @property
    def ready(self):
        return self.current_cooldown <= 0

    @property
    def cooldown_ratio(self):
        if self.max_cooldown <= 0:
            return 0.0
        return max(0.0, self.current_cooldown / self.max_cooldown)

    def update(self, dt):
        if self.current_cooldown > 0:
            self.current_cooldown -= dt
            if self.current_cooldown < 0:
                self.current_cooldown = 0.0

    def use(self, player, gs):
        """스킬 사용. 성공 시 True + 이펙트 반환, 실패 시 False"""
        if self.current_cooldown > 0:
            return False, None
        if player.dead:
            return False, None

        self.current_cooldown = self.max_cooldown
        effects = self._spawn_effects(player, gs)
        return True, effects

    def _spawn_effects(self, player, gs):
        """스킬 타입별 이펙트 생성. SkillProjectile 리스트 반환"""
        effects = []
        px, py = player.rect.centerx, player.rect.centery
        facing = player.facing

        if self.skill_type == 'projectile':
            # 전방 발사체 — 크고 빠르게
            proj = SkillProjectile(
                px + facing * 30, py - 5,
                facing * 12, 0,
                self.color, size=28, lifespan=900, damage=self.damage,
                shape='circle', effect_type='projectile'
            )
            effects.append(proj)
            # 발사 파티클
            gs.particles.emit(px + facing * 20, py, self.color, count=6, lifespan=200)

        elif self.skill_type == 'multi_projectile':
            # 3갈래 발사체 (매직클로) — 더 넓게 퍼지게
            for i in range(3):
                spread = (i - 1) * 2.5
                proj = SkillProjectile(
                    px + facing * 30, py - 5 + spread * 5,
                    facing * 12, spread * 1.2,
                    self.color, size=16, lifespan=600, damage=self.damage,
                    shape='star', effect_type='projectile'
                )
                effects.append(proj)
            gs.particles.emit(px + facing * 20, py, self.color, count=10, lifespan=250)

        elif self.skill_type == 'dash':
            # 순간이동 (플래시 점프)
            dash_dist = 150 * facing
            player.rect.x += dash_dist
            # 화면 경계
            if player.rect.left < 0:
                player.rect.left = 0
            if player.rect.right > SCREEN_W:
                player.rect.right = SCREEN_W
            # 대시 이펙트
            gs.particles.emit(px, py, self.color, count=15, lifespan=300)
            gs.shake.trigger(duration=80, intensity=5.0)

        elif self.skill_type == 'buff':
            # 버프 스킬 (쿨다운 감소)
            self.buff_timer = self.buff_duration
            gs.buff_multiplier = 2.0
            gs.buff_timer = 5000  # 5초 지속
            gs.buff_color = self.color
            # 버프 이펙트
            for _ in range(3):
                gs.particles.emit(
                    px + random.randint(-30, 30),
                    py + random.randint(-30, 30),
                    self.color, count=8, lifespan=400
                )
            gs.shake.trigger(duration=200, intensity=10.0)

        elif self.skill_type == 'aoe':
            # 광역기 (찍기)
            gs.shake.trigger(duration=150, intensity=12.0)
            gs.particles.emit(px, py + 20, self.color, count=15, lifespan=400)
            # 전방 광역 hitbox
            aoe_w, aoe_h = 120, 80
            if facing == 1:
                hitbox = pygame.Rect(px, py - aoe_h // 2, aoe_w, aoe_h)
            else:
                hitbox = pygame.Rect(px - aoe_w, py - aoe_h // 2, aoe_w, aoe_h)
            # AOE용 특수 projectile
            aoe = SkillProjectile(
                hitbox.centerx, hitbox.centery, 0, 0,
                self.color, size=aoe_w, lifespan=200, damage=self.damage,
                shape='rect', effect_type='aoe'
            )
            aoe.hitbox = hitbox
            effects.append(aoe)

        elif self.skill_type == 'ultimate':
            # 궁극기 — 전방 거대 검기
            proj = SkillProjectile(
                px + facing * 40, py - 10,
                facing * 16, 0,
                self.color, size=52, lifespan=1200, damage=self.damage,
                shape='slash', effect_type='projectile'
            )
            effects.append(proj)
            gs.shake.trigger(duration=300, intensity=15.0)
            gs.particles.emit(px + facing * 50, py, self.color, count=20, lifespan=500)

        return effects


# ═══════════════════════════════════════════════════════════════════════════════
# 스킬 매니저
# ═══════════════════════════════════════════════════════════════════════════════

class SkillManager:
    def __init__(self):
        self.skills = [
            Skill("에너지 볼트",  "Q", pygame.K_q, 3000,  (80,  180, 255),
                  "전방 발사체", skill_type='projectile', damage=1),
            Skill("매직 클로",   "W", pygame.K_w, 5000,  (255, 100, 255),
                  "3갈래 발사",  skill_type='multi_projectile', damage=1),
            Skill("플래시 점프", "E", pygame.K_e, 2500,  (50,  255, 100),
                  "전방 순간이동", skill_type='dash', damage=0),
            Skill("부스트",      "R", pygame.K_r, 20000, (255, 200, 50),
                  "5초간 공격력 2배", skill_type='buff', damage=0),
        ]
        self.projectiles = []

    def update(self, dt, platforms=None):
        # 스킬 쿨다운
        for skill in self.skills:
            skill.update(dt)

        # 발사체 업데이트
        for p in self.projectiles:
            p.update(dt, platforms)
        self.projectiles = [p for p in self.projectiles if p.alive]

    def use_skill(self, index, player, gs):
        if index < 0 or index >= len(self.skills):
            return False
        success, effects = self.skills[index].use(player, gs)
        if success and effects:
            self.projectiles.extend(effects)
        return success

    def draw_skills(self, surf, player_rect):
        """스킬바 렌더링 (화면 우하단)"""
        px = 20
        py = SCREEN_H - 50 * len(self.skills) - 20
        slot_w = 45
        slot_h = 45
        gap = 4

        for i, skill in enumerate(self.skills):
            x = px
            y = py + i * (slot_h + gap)

            # 슬롯 배경
            bg_color = (30, 30, 40) if skill.ready else (20, 20, 25)
            pygame.draw.rect(surf, bg_color, (x, y, slot_w, slot_h), border_radius=4)
            pygame.draw.rect(surf, (80, 80, 90), (x, y, slot_w, slot_h), 2, border_radius=4)

            # 쿨다운 오버레이
            if not skill.ready:
                cd_h = int(slot_h * skill.cooldown_ratio)
                if cd_h > 0:
                    cd_surf = pygame.Surface((slot_w, cd_h), pygame.SRCALPHA)
                    cd_surf.fill((40, 40, 60, 160))
                    surf.blit(cd_surf, (x, y + slot_h - cd_h))

            # 스킬 색상 표시
            inner = pygame.Rect(x + 5, y + 5, slot_w - 10, slot_h - 10)
            pygame.draw.rect(surf, skill.color, inner, border_radius=3)

            # 키 라벨
            try:
                font = pygame.font.SysFont("AppleGothic", 14)
            except Exception:
                font = pygame.font.Font(None, 14)
            label = font.render(skill.key_label, True, (255, 255, 255))
            surf.blit(label, (x + slot_w // 2 - label.get_width() // 2, y + slot_h // 2 - 6))

            # 쿨다운 숫자
            if not skill.ready:
                cd_sec = int(skill.current_cooldown / 1000) + 1
                cd_text = font.render(str(cd_sec), True, (255, 200, 200))
                surf.blit(cd_text, (x + slot_w - cd_text.get_width() - 3, y + 3))

            # 마우스오버 시 설명 (고정 툴팁)
            if y < 200:  # 화면 위쪽이면 아래로
                tip_y = y + slot_h + 2
            else:
                tip_y = y - 2
            try:
                font_sm = pygame.font.SysFont("AppleGothic", 12)
            except Exception:
                font_sm = pygame.font.Font(None, 12)
            desc = font_sm.render(skill.description, True, (180, 180, 200))
            surf.blit(desc, (x + slot_w + 8, tip_y + 15))

    def draw_projectiles(self, surf):
        for p in self.projectiles:
            p.draw(surf)