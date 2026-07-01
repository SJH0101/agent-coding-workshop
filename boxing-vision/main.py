"""
Boxing Vision Game — 메인 런처.
Pygame 1인칭 복싱 전투 시작.
"""

import sys
from scenes.fight import run_fight


def main():
    print("=== Boxing Vision Game ===")
    print("웹캠으로 펀치를 날려 상대를 쓰러뜨려라!")
    print("ESC: 종료 | R: 재시작")

    try:
        run_fight()
    except KeyboardInterrupt:
        pass
    finally:
        print("게임 종료.")


if __name__ == "__main__":
    main()
