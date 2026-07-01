import pygame
import random
import sys
import numpy as np

# ── 화면 설정 (MacBook Pro 15") ───────────────────────────────────────────────
SCREEN_W = 1440
SCREEN_H = 900

COLS = 10
ROWS = 20
CELL = 40

BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
BOARD_X = (SCREEN_W - BOARD_W - 260) // 2
BOARD_Y = (SCREEN_H - BOARD_H) // 2
PANEL_X = BOARD_X + BOARD_W + 24
PANEL_Y = BOARD_Y

# ── 색상 ──────────────────────────────────────────────────────────────────────
BLACK     = (5,   5,  15)
DARK      = (12, 12,  28)
GRID_COL  = (25, 25,  55)
WHITE     = (220, 220, 255)

# 네온 컬러 (RGB)
NEON = {
    'I': (0,   255, 255),   # 시안
    'O': (255, 230,   0),   # 옐로
    'T': (200,   0, 255),   # 퍼플
    'S': (0,   255, 100),   # 그린
    'Z': (255,  30,  80),   # 레드
    'J': (30,  120, 255),   # 블루
    'L': (255, 140,   0),   # 오렌지
}

# ── 테트로미노 ────────────────────────────────────────────────────────────────
TETROMINOES = {
    'I': [[(0,1),(1,1),(2,1),(3,1)], [(2,0),(2,1),(2,2),(2,3)],
          [(0,2),(1,2),(2,2),(3,2)], [(1,0),(1,1),(1,2),(1,3)]],
    'O': [[(1,0),(2,0),(1,1),(2,1)]]*4,
    'T': [[(1,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(2,1),(1,2)],
          [(0,1),(1,1),(2,1),(1,2)], [(1,0),(0,1),(1,1),(1,2)]],
    'S': [[(1,0),(2,0),(0,1),(1,1)], [(1,0),(1,1),(2,1),(2,2)],
          [(1,1),(2,1),(0,2),(1,2)], [(0,0),(0,1),(1,1),(1,2)]],
    'Z': [[(0,0),(1,0),(1,1),(2,1)], [(2,0),(1,1),(2,1),(1,2)],
          [(0,1),(1,1),(1,2),(2,2)], [(1,0),(0,1),(1,1),(0,2)]],
    'J': [[(0,0),(0,1),(1,1),(2,1)], [(1,0),(2,0),(1,1),(1,2)],
          [(0,1),(1,1),(2,1),(2,2)], [(1,0),(1,1),(0,2),(1,2)]],
    'L': [[(2,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(1,2),(2,2)],
          [(0,1),(1,1),(2,1),(0,2)], [(0,0),(1,0),(1,1),(1,2)]],
}

WALL_KICKS = {
    (0,1):[( 0,0),(-1,0),(-1,-1),(0, 2),(-1, 2)],
    (1,0):[( 0,0),( 1,0),( 1, 1),(0,-2),( 1,-2)],
    (1,2):[( 0,0),( 1,0),( 1, 1),(0,-2),( 1,-2)],
    (2,1):[( 0,0),(-1,0),(-1,-1),(0, 2),(-1, 2)],
    (2,3):[( 0,0),( 1,0),( 1,-1),(0, 2),( 1, 2)],
    (3,2):[( 0,0),(-1,0),(-1, 1),(0,-2),(-1,-2)],
    (3,0):[( 0,0),(-1,0),(-1, 1),(0,-2),(-1,-2)],
    (0,3):[( 0,0),( 1,0),( 1,-1),(0, 2),( 1, 2)],
}
WALL_KICKS_I = {
    (0,1):[( 0,0),(-2,0),( 1,0),(-2, 1),( 1,-2)],
    (1,0):[( 0,0),( 2,0),(-1,0),( 2,-1),(-1, 2)],
    (1,2):[( 0,0),(-1,0),( 2,0),(-1,-2),( 2, 1)],
    (2,1):[( 0,0),( 1,0),(-2,0),( 1, 2),(-2,-1)],
    (2,3):[( 0,0),( 2,0),(-1,0),( 2,-1),(-1, 2)],
    (3,2):[( 0,0),(-2,0),( 1,0),(-2, 1),( 1,-2)],
    (3,0):[( 0,0),( 1,0),(-2,0),( 1, 2),(-2,-1)],
    (0,3):[( 0,0),(-1,0),( 2,0),(-1,-2),( 2, 1)],
}

# ── BGM 생성 (pygame 합성음) ──────────────────────────────────────────────────
SAMPLE_RATE = 44100

def _wave(freq, dur, vol=0.3, wave='square', decay=0.0):
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, False)
    if wave == 'square':
        w = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave == 'saw':
        w = 2 * (t * freq - np.floor(t * freq + 0.5))
    else:
        w = np.sin(2 * np.pi * freq * t)
    if decay > 0:
        env = np.exp(-decay * t)
        w = w * env
    return (w * vol * 32767).astype(np.int16)

def _silence(dur):
    return np.zeros(int(SAMPLE_RATE * dur), dtype=np.int16)

def build_bgm():
    """
    신나는 8비트 스타일 루프 BGM.
    BPM=160, 4/4 박자, 멜로디 + 베이스 레이어.
    """
    BPM = 160
    beat = 60.0 / BPM        # 0.375s
    e = beat / 2             # 8분음표
    s = beat / 4             # 16분음표

    # 주요 음계 (Hz)
    NOTE = {
        'C4':261.6,'D4':293.7,'E4':329.6,'F4':349.2,'G4':392.0,
        'A4':440.0,'B4':493.9,'C5':523.3,'D5':587.3,'E5':659.3,
        'F5':698.5,'G5':784.0,'A5':880.0,'_':0,
        'C3':130.8,'G3':196.0,'A3':220.0,'F3':174.6,'E3':164.8,
    }

    def n(name, dur, vol=0.25, wave='square', decay=3.0):
        if name == '_' or NOTE[name] == 0:
            return _silence(dur)
        return _wave(NOTE[name], dur, vol, wave, decay)

    # 멜로디 (2마디 x 2 반복 = 4마디 루프)
    mel = np.concatenate([
        # 마디 1
        n('E5',e), n('E5',e), n('_',s), n('E5',s), n('_',e), n('C5',e), n('E5',e),
        n('G5',beat), n('_',beat),
        # 마디 2
        n('G4',beat), n('_',beat), n('C5',beat+e), n('G4',e),
        n('_',e), n('E4',beat), n('A4',beat), n('B4',beat),
        # 마디 3
        n('Bb4',e) if False else n('A5',e), n('A5',e), n('G5',e*1.5), n('E5',s),
        n('G5',e), n('A5',beat), n('F5',e), n('G5',e),
        # 마디 4
        n('_',e), n('E5',beat), n('C5',e), n('D5',e), n('B4',beat+e),
    ])

    # 베이스 (단순 루프)
    def b(name, dur):
        return n(name, dur, vol=0.18, wave='saw', decay=4.0)

    bass_bar = np.concatenate([
        b('C3', beat), b('C3', beat), b('G3', beat), b('G3', beat),
        b('A3', beat), b('A3', beat), b('F3', beat), b('F3', beat),
    ])
    bass = np.tile(bass_bar, int(np.ceil(len(mel) / len(bass_bar))) + 1)[:len(mel)]

    # 믹스 (클리핑 방지)
    mix = mel.astype(np.float32) + bass.astype(np.float32)
    mix = np.clip(mix, -32767, 32767).astype(np.int16)

    # stereo
    stereo = np.column_stack([mix, mix])
    return pygame.sndarray.make_sound(stereo)


# ── 네온 글로우 렌더링 ─────────────────────────────────────────────────────────

def neon_surface(color, w, h, glow_r=12, alpha_core=220):
    """네온 글로우 셀 Surface 생성 (캐시용)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    r, g, b = color

    # 글로우 레이어 (바깥 → 안)
    for i in range(glow_r, 0, -1):
        a = int(alpha_core * (1 - i / glow_r) ** 1.6 * 0.55)
        if a <= 0:
            continue
        gw, gh = w + i*2, h + i*2
        gs = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.rect(gs, (r, g, b, a), (0, 0, gw, gh), border_radius=4)
        surf.blit(gs, (-i, -i))

    # 코어 블록
    pygame.draw.rect(surf, (r, g, b, alpha_core), (0, 0, w, h), border_radius=2)

    # 내부 하이라이트 (밝은 중심선)
    hi = tuple(min(255, c + 120) for c in color)
    pygame.draw.rect(surf, (*hi, 180), (2, 2, w - 4, 4), border_radius=1)
    pygame.draw.rect(surf, (*hi, 100), (2, 2, 4, h - 4), border_radius=1)

    # 스캔라인 효과 (미래적 느낌)
    for y in range(4, h, 6):
        pygame.draw.line(surf, (0, 0, 0, 40), (2, y), (w - 3, y))

    return surf


_CELL_CACHE: dict = {}

def get_cell_surf(kind, size=CELL-1, ghost=False):
    key = (kind, size, ghost)
    if key not in _CELL_CACHE:
        color = NEON[kind]
        if ghost:
            dim = tuple(c // 5 for c in color)
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(s, (*dim, 80), (0, 0, size, size), border_radius=2)
            pygame.draw.rect(s, (*color, 90), (0, 0, size, size), 1, border_radius=2)
            _CELL_CACHE[key] = s
        else:
            _CELL_CACHE[key] = neon_surface(color, size, size)
    return _CELL_CACHE[key]


def draw_cell(surf, col, row, kind, ghost=False, ox=BOARD_X, oy=BOARD_Y):
    s = get_cell_surf(kind, CELL - 1, ghost)
    surf.blit(s, (ox + col * CELL, oy + row * CELL))


def draw_mini_cell(surf, dx, dy, kind, ox, oy, cell=26):
    s = get_cell_surf(kind, cell - 1)
    surf.blit(s, (ox + dx * cell, oy + dy * cell))


# ── 게임 로직 ─────────────────────────────────────────────────────────────────

class Piece:
    def __init__(self, kind=None):
        self.kind = kind or random.choice(list(TETROMINOES))
        self.rotation = 0
        self.x = 3
        self.y = 0

    def cells(self, rot=None, ox=None, oy=None):
        r  = self.rotation if rot is None else rot
        bx = self.x if ox is None else ox
        by = self.y if oy is None else oy
        return [(bx + dx, by + dy) for dx, dy in TETROMINOES[self.kind][r]]

    def rotate_cw(self):  return (self.rotation + 1) % 4
    def rotate_ccw(self): return (self.rotation - 1) % 4


class Board:
    def __init__(self):
        self.grid = [[None]*COLS for _ in range(ROWS)]

    def valid(self, cells):
        return all(0 <= cx < COLS and cy < ROWS and (cy < 0 or self.grid[cy][cx] is None)
                   for cx, cy in cells)

    def lock(self, piece):
        for cx, cy in piece.cells():
            if 0 <= cy < ROWS and 0 <= cx < COLS:
                self.grid[cy][cx] = piece.kind

    def clear_lines(self):
        full = [r for r in range(ROWS) if all(self.grid[r])]
        for r in full:
            del self.grid[r]
            self.grid.insert(0, [None]*COLS)
        return len(full)

    def is_game_over(self):
        return any(self.grid[0][c] for c in range(COLS))


class Game:
    SCORE_TABLE = {1:100, 2:300, 3:500, 4:1200}

    def __init__(self):
        self.board      = Board()
        self.bag        = []
        self.current    = self._next_piece()
        self.next_pieces= [self._next_piece() for _ in range(3)]
        self.hold       = None
        self.hold_used  = False
        self.score      = 0
        self.lines      = 0
        self.level      = 1
        self.game_over  = False
        self.paused     = False
        self._fall_t    = 0
        self._lock_t    = 0
        self._lock_delay= 500

    def _next_piece(self):
        if not self.bag:
            self.bag = list(TETROMINOES)
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    def _fall_ms(self):
        intervals = [800,717,633,550,467,383,300,217,133,100,83,83,83,67,67,67,50,50,50,33]
        return intervals[min(self.level-1, len(intervals)-1)]

    def _ghost_y(self):
        dy = 0
        while self.board.valid(self.current.cells(oy=self.current.y + dy + 1)):
            dy += 1
        return self.current.y + dy

    def _try_rotate(self, new_rot):
        kind = self.current.kind
        kicks = WALL_KICKS_I if kind == 'I' else WALL_KICKS
        for ox, oy in kicks.get((self.current.rotation, new_rot), [(0,0)]):
            if self.board.valid(self.current.cells(rot=new_rot,
                                                   ox=self.current.x+ox,
                                                   oy=self.current.y+oy)):
                self.current.rotation = new_rot
                self.current.x += ox
                self.current.y += oy
                return True
        return False

    def move(self, dx):
        nx = self.current.x + dx
        if self.board.valid(self.current.cells(ox=nx)):
            self.current.x = nx

    def rotate_cw(self):  self._try_rotate(self.current.rotate_cw())
    def rotate_ccw(self): self._try_rotate(self.current.rotate_ccw())

    def soft_drop(self):
        if self.board.valid(self.current.cells(oy=self.current.y+1)):
            self.current.y += 1
            self.score += 1
            self._fall_t = 0
            return True
        return False

    def hard_drop(self):
        drop = 0
        while self.board.valid(self.current.cells(oy=self.current.y+1)):
            self.current.y += 1
            drop += 1
        self.score += drop * 2
        self._lock_piece()

    def hold_piece(self):
        if self.hold_used: return
        if self.hold is None:
            self.hold = self.current.kind
            self.current = self.next_pieces.pop(0)
            self.next_pieces.append(self._next_piece())
        else:
            self.hold, self.current = self.current.kind, Piece(self.hold)
        self.hold_used = True

    def _lock_piece(self):
        self.board.lock(self.current)
        cleared = self.board.clear_lines()
        if cleared:
            self.score += self.SCORE_TABLE.get(cleared, 0) * self.level
            self.lines += cleared
            self.level  = self.lines // 10 + 1
        self.current    = self.next_pieces.pop(0)
        self.next_pieces.append(self._next_piece())
        self.hold_used  = False
        self._lock_t    = 0
        self._fall_t    = 0
        if self.board.is_game_over():
            self.game_over = True

    def update(self, dt):
        if self.game_over or self.paused: return
        on_ground = not self.board.valid(self.current.cells(oy=self.current.y+1))
        if on_ground:
            self._lock_t += dt
            if self._lock_t >= self._lock_delay:
                self._lock_piece()
        else:
            self._lock_t  = 0
            self._fall_t += dt
            if self._fall_t >= self._fall_ms():
                self.current.y += 1
                self._fall_t = 0


# ── 렌더링 ────────────────────────────────────────────────────────────────────

def draw_board(surf, board):
    # 배경 + 테두리 글로우
    glow_rect = pygame.Rect(BOARD_X-3, BOARD_Y-3, BOARD_W+6, BOARD_H+6)
    pygame.draw.rect(surf, (0, 180, 255, 40), glow_rect, 3, border_radius=4)
    pygame.draw.rect(surf, (0, 80, 140), glow_rect, 1, border_radius=4)
    pygame.draw.rect(surf, DARK, (BOARD_X, BOARD_Y, BOARD_W, BOARD_H))

    # 그리드 라인
    for c in range(COLS+1):
        pygame.draw.line(surf, GRID_COL,
                         (BOARD_X + c*CELL, BOARD_Y),
                         (BOARD_X + c*CELL, BOARD_Y + BOARD_H))
    for r in range(ROWS+1):
        pygame.draw.line(surf, GRID_COL,
                         (BOARD_X, BOARD_Y + r*CELL),
                         (BOARD_X + BOARD_W, BOARD_Y + r*CELL))

    for r in range(ROWS):
        for c in range(COLS):
            if board.grid[r][c]:
                draw_cell(surf, c, r, board.grid[r][c])


def draw_piece(surf, piece, ghost_y=None):
    if ghost_y is not None:
        for cx, cy in piece.cells(oy=ghost_y):
            if cy >= 0:
                draw_cell(surf, cx, cy, piece.kind, ghost=True)
    for cx, cy in piece.cells():
        if cy >= 0:
            draw_cell(surf, cx, cy, piece.kind)


def draw_mini(surf, kind, box_rect, cell=26):
    shapes = TETROMINOES[kind][0]
    mx = min(dx for dx, dy in shapes)
    my = min(dy for dx, dy in shapes)
    mw = (max(dx for dx, dy in shapes) - mx + 1) * cell
    mh = (max(dy for dx, dy in shapes) - my + 1) * cell
    ox = box_rect.x + (box_rect.w - mw) // 2
    oy = box_rect.y + (box_rect.h - mh) // 2
    for dx, dy in shapes:
        draw_mini_cell(surf, dx - mx, dy - my, kind, ox, oy, cell)


def panel_box(surf, x, y, w, h, label, font):
    # 패널 박스 네온 테두리
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (20, 20, 45), rect, border_radius=6)
    pygame.draw.rect(surf, (0, 180, 255, 80), rect, 1, border_radius=6)
    lbl = font.render(label, True, (0, 200, 255))
    surf.blit(lbl, (x + 6, y - 22))
    return rect


def draw_panel(surf, game, font_big, font_mid, font_sm):
    px, py = PANEL_X, PANEL_Y

    # HOLD
    box = panel_box(surf, px, py+22, 140, 90, "HOLD", font_sm)
    if game.hold:
        col_mod = NEON[game.hold] if not game.hold_used else tuple(c//3 for c in NEON[game.hold])
        _CELL_CACHE.pop((game.hold, 25, False), None)  # 홀드 사용시 dim
        draw_mini(surf, game.hold, box, cell=26)

    # NEXT x3
    ny = py + 140
    font_sm_r = font_sm.render("NEXT", True, (0, 200, 255))
    surf.blit(font_sm_r, (px+6, ny-22))
    for i, np_piece in enumerate(game.next_pieces):
        box2 = pygame.Rect(px, ny + i*100, 140, 88)
        pygame.draw.rect(surf, (20, 20, 45), box2, border_radius=6)
        pygame.draw.rect(surf, (0, 180, 255, 60), box2, 1, border_radius=6)
        draw_mini(surf, np_piece.kind, box2, cell=24)

    # SCORE / LEVEL / LINES
    sy = py + 450
    for lbl_text, val_text, val_col in [
        ("SCORE", f"{game.score:,}", (255, 220, 50)),
        ("LEVEL", str(game.level),   (0, 255, 180)),
        ("LINES", str(game.lines),   (200, 100, 255)),
    ]:
        l = font_sm.render(lbl_text, True, (120, 180, 255))
        v = font_mid.render(val_text, True, val_col)
        surf.blit(l, (px, sy))
        surf.blit(v, (px, sy+20))
        sy += 72

    # 조작법
    sy += 10
    for line in ["← → : 이동","↑ : 시계 회전","Z : 반시계","↓ : 소프트 드롭",
                 "SPACE : 하드 드롭","C : 홀드","P : 일시정지"]:
        surf.blit(font_sm.render(line, True, (80, 100, 140)), (px, sy))
        sy += 21


def draw_overlay(surf, text, font_big, font_mid):
    ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    ov.fill((0, 0, 10, 180))
    surf.blit(ov, (0, 0))
    # 글로우 텍스트
    for offset, alpha in [(4, 60), (2, 120), (0, 255)]:
        col = (0, 220, 255, alpha)
        t = font_big.render(text, True, (0, 220, 255))
        rect = t.get_rect(center=(SCREEN_W//2 + offset, SCREEN_H//2 - 30 + offset))
        surf.blit(t, rect)
    t2 = font_mid.render("R: 재시작   Q: 종료", True, (150, 150, 200))
    surf.blit(t2, t2.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 30)))


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
    pygame.init()
    pygame.mixer.init(SAMPLE_RATE, -16, 2, 512)

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("TETRIS — NEON FUTURE")
    clock = pygame.time.Clock()

    def get_font(size):
        for name in ["AppleGothic", "AppleSDGothicNeo-Regular", "Arial Unicode MS", ""]:
            try: return pygame.font.SysFont(name, size)
            except: pass
        return pygame.font.Font(None, size)

    font_big = get_font(44)
    font_mid = get_font(30)
    font_sm  = get_font(19)

    # BGM 빌드 & 루프
    try:
        bgm = build_bgm()
        bgm.play(loops=-1)
        bgm_on = True
    except Exception as e:
        print(f"BGM 로드 실패: {e}")
        bgm = None
        bgm_on = False

    game = Game()

    # DAS 설정 (좌/우 이동)
    DAS_DELAY, DAS_REP = 170, 50
    das_dir, das_t, das_active = 0, 0, False

    # 소프트 드롭 DAS
    SD_DELAY, SD_REP = 100, 40
    sd_down, sd_t, sd_active = False, 0, False

    while True:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_q: pygame.quit(); sys.exit()
                if k == pygame.K_r:
                    game = Game()
                    das_dir = das_t = 0; das_active = False
                    sd_down = sd_active = False; sd_t = 0
                    continue
                if game.game_over: continue
                if k == pygame.K_p:
                    game.paused = not game.paused
                if game.paused: continue

                if k == pygame.K_LEFT:
                    game.move(-1); das_dir=-1; das_t=0; das_active=False
                elif k == pygame.K_RIGHT:
                    game.move(1);  das_dir= 1; das_t=0; das_active=False
                elif k == pygame.K_UP:    game.rotate_cw()
                elif k == pygame.K_z:     game.rotate_ccw()
                elif k == pygame.K_DOWN:
                    game.soft_drop()
                    sd_down=True; sd_t=0; sd_active=False
                elif k == pygame.K_SPACE: game.hard_drop()
                elif k == pygame.K_c:     game.hold_piece()
                elif k == pygame.K_m:
                    if bgm:
                        if bgm_on: bgm.stop()
                        else:      bgm.play(loops=-1)
                        bgm_on = not bgm_on

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    das_dir = 0; das_active = False
                if event.key == pygame.K_DOWN:
                    sd_down = False; sd_active = False; sd_t = 0

        # 좌/우 DAS
        if das_dir and not game.game_over and not game.paused:
            das_t += dt
            if not das_active:
                if das_t >= DAS_DELAY: das_active=True; das_t=0
            else:
                if das_t >= DAS_REP: game.move(das_dir); das_t=0

        # 소프트 드롭 DAS (꾹 누르면 연속 하강)
        if sd_down and not game.game_over and not game.paused:
            sd_t += dt
            if not sd_active:
                if sd_t >= SD_DELAY: sd_active=True; sd_t=0
            else:
                if sd_t >= SD_REP: game.soft_drop(); sd_t=0

        game.update(dt)

        # ── 렌더링 ──────────────────────────────────
        screen.fill(BLACK)

        # 배경 스캔라인 효과
        scan_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 4):
            pygame.draw.line(scan_surf, (0, 0, 0, 18), (0, y), (SCREEN_W, y))
        screen.blit(scan_surf, (0, 0))

        draw_board(screen, game.board)
        draw_piece(screen, game.current, ghost_y=game._ghost_y())
        draw_panel(screen, game, font_big, font_mid, font_sm)

        # M키 BGM 힌트
        hint = font_sm.render("M: 음악 ON/OFF", True, (50, 70, 110))
        screen.blit(hint, (BOARD_X, BOARD_Y + BOARD_H + 8))

        if game.paused and not game.game_over:
            draw_overlay(screen, "PAUSE", font_big, font_mid)
        if game.game_over:
            draw_overlay(screen, "GAME OVER", font_big, font_mid)

        pygame.display.flip()


if __name__ == "__main__":
    main()
