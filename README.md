# agent-coding-workshop

멀티 프로젝트 워크스페이스.

## 프로젝트 목록

### 1. UNIST Boss Game (`unist-boss/`)

Pygame 기반 자쿰 오마주 보스전 게임. 교수 캐릭터(패러디) 8개 팔과 전투.

```bash
cd unist-boss
python main.py
```

> pygame 필요: `pip install pygame` 또는 `uv add pygame`

**조작키**: ← → 이동, ↑ 사다리, V 점프, ↓+V 낙하, C 공격, Q/W/E/R 스킬
**공략**: 방패팔(파란 원) 제외 7개 팔 파괴 → 방패팔 파괴 → 보스 본체 → A+ 승리

### 2. Boxing Vision Game (`boxing-vision/`)

웹캠 + MediaPipe 기반 복싱 게임. 실제 펀치 동작 인식.

```bash
cd boxing-vision
pip install opencv-python mediapipe
python main.py
```

### 3. Tetris (`tetris/`)

Pygame 테트리스.

```bash
cd tetris
python main.py
```

### 4. Bucket List Map (`bucket-list-map/`)

Leaflet 기반 버킷리스트 지도 앱.

브라우저에서 `bucket-list-map/index.html` 열기.