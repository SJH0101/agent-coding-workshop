"""Stage 1 검증 스크립트"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["DISPLAY"] = ""

import pygame

pygame.init()
pygame.display.set_mode((320, 200))

sys.path.insert(0, os.path.dirname(__file__))
from main import Player, SCREEN_W, SCREEN_H, GRAVITY, JUMP_VEL, MOVE_SPEED, ATTACK_DUR


class KeyState:
    """pygame.key.get_pressed()와 호환되는 mock — 큰 상수값(K_LEFT 등)도 안전하게 처리"""
    def __init__(self, *down_keys):
        self._down = set(down_keys)

    def __getitem__(self, idx):
        return 1 if idx in self._down else 0

    def __len__(self):
        return 512

    def __iter__(self):
        return iter([0] * 512)


def test_gravity_and_landing():
    p = Player()
    p.vy = JUMP_VEL
    p.on_ground = False

    for frame in range(200):
        p.update(KeyState(), 16)
        if p.rect.bottom == SCREEN_H and p.on_ground:
            print(f"  ✅ frame={frame}, bottom={p.rect.bottom}, vy={p.vy:.2f}")
            return True

    print(f"  ❌ 실패: bottom={p.rect.bottom}, on_ground={p.on_ground}")
    return False


def test_horizontal_movement():
    p = Player()
    x0 = p.rect.x

    # → 오른쪽 이동 (D)
    for _ in range(10):
        p.update(KeyState(pygame.K_d, pygame.K_RIGHT), 16)
    assert p.rect.x > x0, f"오른쪽 이동 실패: {x0} → {p.rect.x}"

    # → 왼쪽 이동 (A)
    x0 = p.rect.x
    for _ in range(10):
        p.update(KeyState(pygame.K_a, pygame.K_LEFT), 16)
    assert p.rect.x < x0, f"왼쪽 이동 실패: {x0} → {p.rect.x}"
    assert p.facing == -1, f"facing={p.facing} (expected -1)"

    print(f"  ✅ 정상")
    return True


def test_jump_via_key():
    p = Player()
    # 바닥에 먼저 착지
    for _ in range(200):
        p.update(KeyState(), 16)
    assert p.on_ground

    # 점프
    p.update(KeyState(pygame.K_SPACE), 16)
    assert not p.on_ground, "점프 후에도 on_ground"
    assert p.vy < 0, f"vy가 음수가 아님: {p.vy}"
    print(f"  ✅ 점프 vy={p.vy:.2f}, on_ground={p.on_ground}")
    return True


def test_attack_timer():
    p = Player()
    p.attacking = True
    p.attack_timer = ATTACK_DUR

    for frame in range(30):
        p.update(KeyState(), 16)
        if not p.attacking:
            print(f"  ✅ frame={frame}, timer={p.attack_timer:.1f}")
            return True

    print(f"  ❌ attacking={p.attacking}, timer={p.attack_timer:.1f}")
    return False


def test_attack_hitbox_via_key():
    p = Player()

    # J 키로 공격 발동
    p.update(KeyState(pygame.K_j), 16)
    assert p.attacking, "공격 발동 안됨"
    assert p.attack_hitbox.width > 0, f"hitbox.width=0, rect={p.attack_hitbox}"
    # 오른쪽 facing에서 hitbox는 플레이어 오른쪽에 위치
    assert p.attack_hitbox.left >= p.rect.right, \
        f"오른쪽 공격: hitbox.left={p.attack_hitbox.left} < player.right={p.rect.right}"
    print(f"  ✅ 오른쪽 공격: hitbox={p.attack_hitbox}")

    # 왼쪽 facing
    p2 = Player()
    p2.rect.x = 200
    p2.facing = -1
    p2.update(KeyState(pygame.K_a, pygame.K_j), 16)
    assert p2.attacking
    assert p2.facing == -1, f"facing={p2.facing}"
    assert p2.attack_hitbox.width > 0
    assert p2.attack_hitbox.right <= p2.rect.left, \
        f"왼쪽 공격: hitbox.right={p2.attack_hitbox.right} > player.left={p2.rect.left}"
    print(f"  ✅ 왼쪽 공격: hitbox={p2.attack_hitbox}")
    return True


def test_screen_bounds():
    p = Player()

    # 왼쪽 경계
    p.rect.x = -50
    for _ in range(5):
        p.update(KeyState(pygame.K_a), 16)
    assert p.rect.left >= 0, f"왼쪽 경계: {p.rect.left}"

    # 오른쪽 경계
    p.rect.x = SCREEN_W + 50
    for _ in range(5):
        p.update(KeyState(pygame.K_d), 16)
    assert p.rect.right <= SCREEN_W, f"오른쪽 경계: {p.rect.right}"

    print(f"  ✅ 정상")
    return True


# ── 실행 ──
tests = [
    ("중력 + 착지", test_gravity_and_landing),
    ("좌우 이동", test_horizontal_movement),
    ("점프 키", test_jump_via_key),
    ("공격 타이머", test_attack_timer),
    ("공격 판정 위치", test_attack_hitbox_via_key),
    ("화면 경계", test_screen_bounds),
]

results = []
for name, fn in tests:
    print(f"\n▶ {name}...")
    try:
        ok = fn()
        results.append((name, "PASS" if ok else "FAIL"))
    except Exception as e:
        results.append((name, f"ERROR: {e}"))

print("\n" + "=" * 40)
print("종합 결과")
for name, status in results:
    mark = "✅" if status == "PASS" else "❌"
    print(f"  {mark} {status}  {name}")

all_pass = all(r[1] == "PASS" for r in results)
print(f"\n{'✅ 전체 통과' if all_pass else '❌ 일부 실패'}")
pygame.quit()
sys.exit(0 if all_pass else 1)