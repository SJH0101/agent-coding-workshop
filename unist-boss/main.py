"""
UNIST Boss Game — Stage 4
8개 팔 전투 + 방패 로직 + 본체 처치 + 승패 엔딩
"""
import pygame
import sys
import math
import random
from scenes.boss import Boss, ParticleSystem, ScreenShake, ArmF, ArmChain, ArmHook
from scenes.skills import SkillManager

SCREEN_W = 1280; SCREEN_H = 720; FPS = 60
TITLE = "UNIST Boss Game"

BG_COLOR = (10, 10, 30)
FLOOR_COLOR = (20, 20, 50)
PLAYER_COLOR = (220, 220, 255)
ATTACK_COLOR = (255, 80, 80)
TEXT_COLOR = (180, 200, 240)

GRAVITY = 0.65; JUMP_VEL = -13.0; MOVE_SPEED = 5.5
ATTACK_DUR = 250; ATTACK_W = 70; ATTACK_H = 50

FLOOR_Y = SCREEN_H - 60

PLATFORMS = [
    pygame.Rect(100,  420, 220, 18),   # 좌측 하단
    pygame.Rect(960,  420, 220, 18),   # 우측 하단
    pygame.Rect(530,  320, 220, 18),   # 중앙
    pygame.Rect(540,  200, 200, 16),   # 상단 (보스 바로 아래)
    pygame.Rect(560,  130, 160, 14),   # 최상단 (보스 옆)
]

LADDERS = [
    pygame.Rect(142,  200, 24, FLOOR_Y - 200),  # 좌측 (상단까지)
    pygame.Rect(1002, 200, 24, FLOOR_Y - 200),  # 우측
]

# ═══════════════════════════════════════════════════════════════════════════════
# 플레이어
# ═══════════════════════════════════════════════════════════════════════════════

class Player:
    def __init__(self):
        self.start_x = 600
        self.start_y = FLOOR_Y - 60
        self.rect = pygame.Rect(self.start_x, self.start_y, 40, 60)
        self.vy = 0.0; self.vx = 0.0
        self.on_ground = False; self.facing = 1
        self.attacking = False; self.attack_timer = 0
        self.attack_hitbox = pygame.Rect(0, 0, 0, 0)
        self.dead = False
        self.climbing = False; self.drop_through = False
        self.drop_timer = 0; self.on_platform = False
        self.rooted = False; self.root_timer = 0
        self._boom_hit_timer = 0
        self.walk_frame = 0.0

    def teleport_start(self):
        self.rect.x = self.start_x
        self.rect.y = self.start_y
        self.vy = 0; self.vx = 0; self.climbing = False

    def update(self, keys_pressed, dt):
        if self.dead:
            return

        # CC: 루트
        if self.rooted:
            self.root_timer -= dt
            if self.root_timer <= 0:
                self.rooted = False
            else:
                self.vx = 0
                if self.attacking:
                    self.attack_timer -= dt
                    if self.attack_timer <= 0:
                        self.attacking = False
                self.vy += GRAVITY
                if self.vy > 20: self.vy = 20
                self.rect.y += self.vy
                if self.rect.bottom >= FLOOR_Y:
                    self.rect.bottom = FLOOR_Y; self.vy = 0; self.on_ground = True
                return

        # ── 사다리 ──
        on_ladder_zone = any(lad.colliderect(self.rect) for lad in LADDERS)
        if on_ladder_zone and keys_pressed[pygame.K_UP]:
            self.climbing = True; self.vy = 0; self.on_ground = False

        if self.climbing:
            self.vy = 0; self.vx = 0; spd = 4
            if keys_pressed[pygame.K_UP]: self.rect.y -= spd
            if keys_pressed[pygame.K_DOWN]: self.rect.y += spd
            if keys_pressed[pygame.K_v]:
                self.climbing = False; self.vy = JUMP_VEL * 0.4
            if not any(lad.colliderect(self.rect) for lad in LADDERS):
                self.climbing = False
            if self.rect.top < 0: self.rect.top = 0
            if self.rect.bottom >= FLOOR_Y:
                self.rect.bottom = FLOOR_Y; self.climbing = False; self.on_ground = True
            return

        # ── 낙하 ──
        if self.drop_through:
            self.drop_timer -= dt
            if self.drop_timer <= 0: self.drop_through = False
        if keys_pressed[pygame.K_DOWN] and keys_pressed[pygame.K_v] \
                and self.on_ground and self.on_platform and not self.drop_through:
            self.drop_through = True; self.drop_timer = 300
            self.rect.y += 5; self.on_ground = False; self.on_platform = False

        # ── 이동 ──
        dx = 0
        if keys_pressed[pygame.K_LEFT]: dx = -MOVE_SPEED; self.facing = -1
        elif keys_pressed[pygame.K_RIGHT]: dx = MOVE_SPEED; self.facing = 1
        self.vx = dx
        if dx != 0 and self.on_ground:
            self.walk_frame += dt * 0.01
        elif self.on_ground:
            self.walk_frame = 0.0

        if keys_pressed[pygame.K_v] and self.on_ground:
            self.vy = JUMP_VEL; self.on_ground = False

        if keys_pressed[pygame.K_c] and not self.attacking:
            self.attacking = True; self.attack_timer = ATTACK_DUR
            if self.facing == 1:
                self.attack_hitbox = pygame.Rect(self.rect.right, self.rect.centery - ATTACK_H//2, ATTACK_W, ATTACK_H)
            else:
                self.attack_hitbox = pygame.Rect(self.rect.left - ATTACK_W, self.rect.centery - ATTACK_H//2, ATTACK_W, ATTACK_H)

        if self.attacking:
            self.attack_timer -= dt
            if self.attack_timer <= 0: self.attacking = False

        self.vy += GRAVITY
        if self.vy > 20: self.vy = 20
        self.rect.x += self.vx; self.rect.y += self.vy

        self.on_platform = False
        if not self.drop_through:
            for plat in PLATFORMS:
                if self.vy >= 0 and self.rect.bottom <= plat.top + self.vy + 6 \
                        and self.rect.bottom + self.vy >= plat.top \
                        and self.rect.right - 4 > plat.left and self.rect.left + 4 < plat.right:
                    self.rect.bottom = plat.top; self.vy = 0.0
                    self.on_ground = True; self.on_platform = True; break

        if self.rect.bottom >= FLOOR_Y:
            self.rect.bottom = FLOOR_Y; self.vy = 0.0; self.on_ground = True; self.on_platform = False
        elif not self.on_platform:
            self.on_ground = False

        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > SCREEN_W: self.rect.right = SCREEN_W

        if self.attacking:
            if self.facing == 1:
                self.attack_hitbox.topleft = (self.rect.right, self.rect.centery - ATTACK_H//2)
            else:
                self.attack_hitbox.topleft = (self.rect.left - ATTACK_W, self.rect.centery - ATTACK_H//2)

    def draw(self, surf):
        if self.dead:
            # 죽은 캐릭터 — X 표시
            r = self.rect
            pygame.draw.rect(surf, (180, 40, 40), r)
            pygame.draw.line(surf, (255, 200, 200), r.topleft, r.bottomright, 3)
            pygame.draw.line(surf, (255, 200, 200), r.topright, r.bottomleft, 3)
            return

        cx = self.rect.centerx
        top = self.rect.top
        w = self.rect.w
        h = self.rect.h
        f = self.facing

        # 색상
        skin = (255, 220, 190)
        hair_c = (80, 50, 30)
        if self.climbing:
            shirt = (100, 160, 220)
        elif self.rooted:
            shirt = (180, 140, 220)
        else:
            shirt = (60, 120, 200)
        pants = (40, 50, 80)
        shoe = (60, 40, 30)

        # === 다리 ===
        leg_h = 16
        leg_y = top + h - leg_h
        if self.vx != 0 and self.on_ground and not self.climbing:
            swing = math.sin(self.walk_frame * math.pi * 2) * 6
            lx = cx - 7 + swing
            rx = cx + 7 - swing
        else:
            lx, rx = cx - 7, cx + 7
        # 왼다리
        pygame.draw.rect(surf, pants, (lx - 5, leg_y, 10, leg_h - 4), border_radius=2)
        # 오른다리
        pygame.draw.rect(surf, pants, (rx - 5, leg_y, 10, leg_h - 4), border_radius=2)
        # 신발
        pygame.draw.ellipse(surf, shoe, (lx - 6, leg_y + leg_h - 6, 12, 6))
        pygame.draw.ellipse(surf, shoe, (rx - 6, leg_y + leg_h - 6, 12, 6))

        # === 몸통 ===
        body_top = top + 18
        body_h = 24
        pygame.draw.rect(surf, shirt, (cx - 12, body_top, 24, body_h), border_radius=4)
        # 셔츠 디테일 (단추)
        for by in (body_top + 6, body_top + 14):
            pygame.draw.circle(surf, (255, 255, 200), (cx, by), 2)

        # === 팔 (움직임) ===
        arm_y = body_top + 6
        shoulder_x = cx - 14 if f == 1 else cx + 14
        if self.attacking:
            # 공격 팔 — 앞으로 쭉
            atk_prog = 1.0 - (self.attack_timer / ATTACK_DUR)
            reach = 10 + atk_prog * 20
            if f == 1:
                hand = (cx + 14 + reach, arm_y - 2)
                shoulder = (cx + 10, arm_y)
            else:
                hand = (cx - 14 - reach, arm_y - 2)
                shoulder = (cx - 10, arm_y)
            # 공격 궤적
            pygame.draw.line(surf, ATTACK_COLOR, shoulder, hand, 5)
            pygame.draw.circle(surf, (255, 200, 200), hand, 5)
        else:
            # 일반 팔
            swing = math.sin(pygame.time.get_ticks() * 0.004) * 2
            if f == 1:
                pygame.draw.line(surf, skin, (cx + 10, arm_y), (cx + 18, arm_y + 10 + swing), 4)
            else:
                pygame.draw.line(surf, skin, (cx - 10, arm_y), (cx - 18, arm_y + 10 + swing), 4)
            # 뒤쪽 팔
            if f == 1:
                pygame.draw.line(surf, (220, 190, 160), (cx + 8, arm_y + 2), (cx + 14, arm_y + 6 - swing), 3)
            else:
                pygame.draw.line(surf, (220, 190, 160), (cx - 8, arm_y + 2), (cx - 14, arm_y + 6 - swing), 3)

        # === 머리 ===
        head_r = 11
        head_y = top + 10
        # 머리
        pygame.draw.circle(surf, skin, (cx, head_y), head_r)
        # 헤어 (앞머리)
        hair_pts = [
            (cx - head_r, head_y - 2),
            (cx - 2, head_y - head_r - 3),
            (cx + 2, head_y - head_r - 3),
            (cx + head_r, head_y - 2),
            (cx + head_r - 3, head_y + 4),
            (cx - head_r + 3, head_y + 4),
        ]
        pygame.draw.polygon(surf, hair_c, hair_pts)
        # 눈 (방향)
        eye_off = 4 if f == 1 else -4
        eye_y = head_y - 1
        pygame.draw.circle(surf, (30, 30, 30), (cx + eye_off - 3, eye_y), 2)
        pygame.draw.circle(surf, (30, 30, 30), (cx + eye_off + 3, eye_y), 2)
        # 눈동자 (초점)
        pygame.draw.circle(surf, (255, 255, 255), (cx + eye_off - 2, eye_y - 1), 1)
        pygame.draw.circle(surf, (255, 255, 255), (cx + eye_off + 4, eye_y - 1), 1)
        # 입
        if self.attacking:
            pygame.draw.arc(surf, (200, 80, 80), (cx - 3, eye_y + 4, 6, 5), 0, math.pi, 2)

        # === 공격 hitbox ===
        if self.attacking:
            alpha = int(120 * max(0.0, self.attack_timer / ATTACK_DUR))
            s = pygame.Surface((ATTACK_W, ATTACK_H), pygame.SRCALPHA)
            s.fill((*ATTACK_COLOR, alpha))
            surf.blit(s, self.attack_hitbox.topleft)
            pygame.draw.rect(surf, ATTACK_COLOR, self.attack_hitbox, 2)

        # === 루트 표시 ===
        if self.rooted:
            cy2 = top - 8
            for i in range(3):
                pygame.draw.circle(surf, (140, 100, 200), (cx + i * 6 - 6, cy2 + i * 3), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# 게임 상태
# ═══════════════════════════════════════════════════════════════════════════════

class GameState:
    PLAYING = 0
    DEAD = 1
    WIN = 2

    def __init__(self):
        self.player = Player()
        self.boss = Boss()
        self.particles = ParticleSystem()
        self.shake = ScreenShake()
        self.skills = SkillManager()
        self.state = self.PLAYING
        self.buff_multiplier = 1.0
        self.buff_timer = 0.0
        self.buff_color = (255, 200, 50)
        self.win_timer = 0.0

    def reset(self):
        self.__init__()


# ═══════════════════════════════════════════════════════════════════════════════
# 충돌 검사
# ═══════════════════════════════════════════════════════════════════════════════

def _hit_arm_effect(gs, arm, x, y, destroyed):
    if destroyed:
        arm.destroy_effect(gs, x, y)
    else:
        arm.hit_effect(gs, x, y)


def check_collisions(gs):
    player = gs.player
    if player.dead or gs.state != GameState.PLAYING:
        return
    buff = gs.buff_multiplier

    # 1) 기본 공격 → 팔 / 본체
    if player.attacking:
        atk = player.attack_hitbox
        hit_something = False

        # 1a) 팔
        for arm in gs.boss.arms:
            if arm.state == arm.STATE_DESTROYED:
                continue
            if not gs.boss.can_damage_arm(arm):
                hurt = arm.get_hurtbox()
                if atk.colliderect(hurt):
                    gs.particles.emit(atk.centerx, atk.centery, (100, 100, 255), count=4, lifespan=200)
                    gs.shake.trigger(duration=60, intensity=3.0)
                    hit_something = True
                continue
            hurt = arm.get_hurtbox()
            if atk.colliderect(hurt):
                dmg = int(1 * buff)
                destroyed = arm.take_damage(dmg)
                _hit_arm_effect(gs, arm, atk.centerx, atk.centery, destroyed)
                hit_something = True; break

        # 1b) 보스 본체
        if not hit_something and gs.boss.is_body_vulnerable():
            if atk.colliderect(gs.boss.rect):
                dmg = int(1 * buff)
                gs.boss.hp -= dmg
                if gs.boss.hp <= 0:
                    gs.boss.hp = 0; gs.boss.defeated = True
                    gs.state = GameState.WIN; gs.win_timer = 0.0
                cx, cy = atk.center
                gs.particles.emit(cx, cy, (200, 100, 255), count=10, lifespan=400)
                gs.shake.trigger(duration=100, intensity=6.0)

    # 2) 스킬 발사체 → 팔 / 본체
    for proj in gs.skills.projectiles[:]:
        if not proj.alive or proj.owner != 'player':
            continue
        proj_hit = False

        for arm in gs.boss.arms:
            if arm.state == arm.STATE_DESTROYED:
                continue
            arm_id = id(arm)
            if proj.has_hit(arm_id):
                continue
            if not gs.boss.can_damage_arm(arm):
                hurt = arm.get_hurtbox()
                if proj.hitbox.colliderect(hurt):
                    gs.particles.emit(proj.hitbox.centerx, proj.hitbox.centery, (100, 100, 255), count=4, lifespan=200)
                    proj_hit = True; break
                continue
            hurt = arm.get_hurtbox()
            if proj.hitbox.colliderect(hurt):
                dmg = int(proj.damage * buff)
                destroyed = arm.take_damage(dmg)
                _hit_arm_effect(gs, arm, proj.hitbox.centerx, proj.hitbox.centery, destroyed)
                proj_hit = True; proj.alive = False; break

        if not proj_hit and gs.boss.is_body_vulnerable():
            if proj.hitbox.colliderect(gs.boss.rect):
                dmg = int(proj.damage * buff)
                gs.boss.hp -= dmg
                if gs.boss.hp <= 0:
                    gs.boss.hp = 0; gs.boss.defeated = True
                    gs.state = GameState.WIN; gs.win_timer = 0.0
                gs.particles.emit(proj.hitbox.centerx, proj.hitbox.centery, (200, 100, 255), count=8, lifespan=400)
                gs.shake.trigger(duration=100, intensity=6.0)
                proj.alive = False

    # 3) 각 팔의 hitbox → 플레이어
    for arm in gs.boss.arms:
        if arm.state == arm.STATE_DESTROYED:
            continue
        if arm.hitbox.width == 0:
            continue
        if not arm.hitbox.colliderect(player.rect):
            continue

        if isinstance(arm, ArmF) and arm.state == arm.STATE_SWING:
            player.dead = True; gs.state = GameState.DEAD
            gs.particles.emit(player.rect.centerx, player.rect.centery, (200, 40, 40), count=25, lifespan=800)
            gs.shake.trigger(duration=400, intensity=16.0)
            return

        if isinstance(arm, ArmChain) and arm.state == arm.STATE_THROW:
            arm.on_hit_player(player)
            gs.particles.emit(player.rect.centerx, player.rect.centery, (100, 200, 100), count=15, lifespan=500)
            gs.shake.trigger(duration=200, intensity=8.0)
            arm.state = arm.STATE_RECOVER; arm.timer = 0.0

        if isinstance(arm, ArmHook) and arm.state == arm.STATE_FIRE:
            arm.on_hit_player(player)
            gs.particles.emit(player.rect.centerx, player.rect.centery, (200, 100, 100), count=12, lifespan=400)

        if arm.name == 'whip' and arm.state == arm.STATE_LASH:
            player.rooted = True; player.root_timer = 500
            gs.particles.emit(player.rect.centerx, player.rect.centery, (160, 80, 200), count=10, lifespan=300)

        if arm.name == 'hammer' and arm.state == arm.STATE_SMASH and arm.smash_progress >= 0.7:
            player.vy = -8
            if player.rect.centerx < arm.smash_x: player.vx = -8
            else: player.vx = 8
            gs.shake.trigger(duration=200, intensity=12.0)

        if arm.name == 'boomerang' and arm.state in (arm.STATE_THROW, arm.STATE_RETURN):
            if player._boom_hit_timer <= 0:
                player.vy = -6
                player._boom_hit_timer = 400
                gs.shake.trigger(duration=100, intensity=7.0)

        if arm.name == 'spear' and arm.state == arm.STATE_THRUST:
            player.vy = -5
            player.vx = -player.facing * 6
            gs.shake.trigger(duration=80, intensity=5.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    gs = GameState()

    try:
        font_sm   = pygame.font.SysFont("AppleGothic", 16)
        font_big  = pygame.font.SysFont("AppleGothic", 52)
        font_mid  = pygame.font.SysFont("AppleGothic", 24)
        font_hud  = pygame.font.SysFont("AppleGothic", 14)
        font_win  = pygame.font.SysFont("AppleGothic", 40)
    except Exception:
        font_sm = font_mid = font_big = font_hud = font_win = pygame.font.Font(None, 24)

    running = True
    while running:
        dt = clock.tick(FPS)
        keys_pressed = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_q:
                    gs.skills.use_skill(0, gs.player, gs)
                if event.key == pygame.K_w:
                    gs.skills.use_skill(1, gs.player, gs)
                if event.key == pygame.K_e:
                    gs.skills.use_skill(2, gs.player, gs)
                if event.key == pygame.K_r:
                    if gs.state in (GameState.DEAD, GameState.WIN):
                        gs.reset()
                    else:
                        gs.skills.use_skill(3, gs.player, gs)

        player = gs.player
        if gs.state == GameState.PLAYING:
            player.update(keys_pressed, dt)
            gs.boss.update(dt, player.rect)
            gs.skills.update(dt, PLATFORMS)
            check_collisions(gs)
            if player._boom_hit_timer > 0:
                player._boom_hit_timer -= dt
        elif gs.state == GameState.WIN:
            gs.win_timer += dt
            if gs.win_timer % 200 < 16:
                gs.particles.emit(
                    random.randint(100, SCREEN_W - 100),
                    random.randint(0, SCREEN_H // 2),
                    random.choice([(255, 200, 50), (255, 100, 100), (100, 200, 255), (200, 100, 255)]),
                    count=3, lifespan=1200)

        gs.particles.update(dt)
        gs.shake.update(dt)

        if gs.buff_timer > 0:
            gs.buff_timer -= dt
            if gs.buff_timer <= 0:
                gs.buff_timer = 0; gs.buff_multiplier = 1.0

        shake_ofs = gs.shake.get_offset()
        screen.fill(BG_COLOR)

        pygame.draw.rect(screen, FLOOR_COLOR, (0, FLOOR_Y, SCREEN_W, SCREEN_H - FLOOR_Y))
        pygame.draw.line(screen, (40, 40, 80), (0, FLOOR_Y), (SCREEN_W, FLOOR_Y), 2)
        for plat in PLATFORMS:
            pygame.draw.rect(screen, (40, 45, 70), plat, border_radius=3)
            pygame.draw.rect(screen, (60, 65, 100), plat, 2, border_radius=3)
        for lad in LADDERS:
            for ry in range(lad.top, lad.bottom, 25):
                pygame.draw.line(screen, (90, 60, 30), (lad.left+4, ry), (lad.right-4, ry), 3)
            pygame.draw.line(screen, (80, 50, 20), (lad.left+4, lad.top), (lad.left+4, lad.bottom), 2)
            pygame.draw.line(screen, (80, 50, 20), (lad.right-4, lad.top), (lad.right-4, lad.bottom), 2)

        bs = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        gs.boss.draw(bs)
        screen.blit(bs, shake_ofs)
        player.draw(screen)

        ps = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        gs.skills.draw_projectiles(ps)
        screen.blit(ps, shake_ofs)

        pts = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        gs.particles.draw(pts)
        screen.blit(pts, shake_ofs)

        gs.skills.draw_skills(screen, player.rect)

        if gs.buff_timer > 0:
            t = font_mid.render(f"부스트! {gs.buff_timer/1000:.1f}초", True, gs.buff_color)
            screen.blit(t, (SCREEN_W//2 - t.get_width()//2, 80))

        if gs.state == GameState.DEAD:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180)); screen.blit(ov, (0, 0))
            t1 = font_big.render("재수강", True, (230, 60, 60))
            screen.blit(t1, t1.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 30)))
            t2 = font_mid.render("R 키로 재시작  /  ESC 키로 종료", True, (200, 200, 200))
            screen.blit(t2, t2.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 30)))

        if gs.state == GameState.WIN:
            ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 140)); screen.blit(ov, (0, 0))
            t1 = font_big.render("완벽한 디펜스", True, (255, 220, 50))
            screen.blit(t1, t1.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 50)))
            glow = int(200 + 55 * math.sin(gs.win_timer / 200))
            t2 = font_win.render("A+", True, (255, glow, 50))
            screen.blit(t2, t2.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 10)))
            t3 = font_mid.render("R 키로 재시작  /  ESC 키로 종료", True, (200, 200, 200))
            screen.blit(t3, t3.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 60)))

        help_lines = [
            "← → Move   ↑ Ladder   V Jump   Down+V Drop",
            "C Attack   Q W E R Skills",
            "ESC Quit   R(dead/win) Restart",
        ]
        y = 10
        for line in help_lines:
            s = font_hud.render(line, True, TEXT_COLOR)
            screen.blit(s, (10, y)); y += 18

        pygame.display.flip()

    pygame.quit(); sys.exit()


if __name__ == "__main__":
    main()