"""
샘플 데이터 생성기 (한 번만 실행하면 됩니다)

목적: 실제 K리그 데이터를 아직 못 구한 상태에서도
      파이프라인 전체(분석 -> 차트 -> 사이트)가 돌아가는지 확인하기 위한 가짜 데이터.

!!! 중요 !!!
여기서 만들어지는 숫자는 전부 '가짜'입니다. 실제 경기 결과가 아닙니다.
실제 데이터를 넣을 때는 data/raw/*.csv 를 직접 덮어쓰면 됩니다.
컬럼 이름만 똑같이 맞추면 나머지 코드는 그대로 돌아갑니다.
"""

import csv
import random
from pathlib import Path

RAW = Path(__file__).parent / "raw"
RAW.mkdir(parents=True, exist_ok=True)

random.seed(42)  # 실행할 때마다 같은 값이 나오도록 고정 (재현성)

MY_TEAM = "대구FC"
OPPONENTS = [
    "충북청주", "부천FC1995", "전남드래곤즈", "서울이랜드",
    "경남FC", "성남FC", "안산그리너스", "천안시티",
]

# 실제 확인된 2026 대구FC 주장단 3명 + 나머지는 자리표시용 가짜 이름
SQUAD = [
    ("세징야", "FW"),
    ("한국영", "MF"),
    ("김강산", "DF"),
    ("예시선수04", "GK"),
    ("예시선수05", "DF"),
    ("예시선수06", "DF"),
    ("예시선수07", "DF"),
    ("예시선수08", "MF"),
    ("예시선수09", "MF"),
    ("예시선수10", "FW"),
    ("예시선수11", "FW"),
    ("예시선수12", "MF"),
    ("예시선수13", "FW"),
]


def main():
    matches, lineups, team_stats, player_stats = [], [], [], []

    for i, opp in enumerate(OPPONENTS * 2, start=1):  # 16경기
        match_id = f"2026-{i:02d}"
        home = MY_TEAM if i % 2 == 1 else opp
        away = opp if i % 2 == 1 else MY_TEAM

        # 결장 기간을 일부러 만들어 둡니다 (On/Off 분석을 시연하기 위한 설정)
        sejinya_out = 5 <= i <= 8
        absent = set()
        if sejinya_out:
            absent.add("세징야")
        if i in (2, 3, 11, 12):
            absent.add("한국영")
        if i in (9, 10, 14):
            absent.add("김강산")

        # 세징야가 있으면 팀이 조금 더 잘한다고 가정한 가짜 숫자
        boost = 0 if sejinya_out else 1
        my_goals = max(0, random.randint(0, 2) + boost)
        opp_goals = max(0, random.randint(0, 2) - boost // 2)

        matches.append({
            "match_id": match_id,
            "date": f"2026-{3 + i // 4:02d}-{(i * 3) % 28 + 1:02d}",
            "round": i,
            "home_team": home,
            "away_team": away,
            "home_score": my_goals if home == MY_TEAM else opp_goals,
            "away_score": my_goals if away == MY_TEAM else opp_goals,
        })

        # --- 팀 단위 기록 (우리 팀 + 상대 팀) ---
        for team, goals, is_mine in [(MY_TEAM, my_goals, True), (opp, opp_goals, False)]:
            pass_att = random.randint(380, 520) + (20 * boost if is_mine else 0)
            pass_cmp = int(pass_att * (random.uniform(0.74, 0.86) + (0.02 * boost if is_mine else 0)))
            team_stats.append({
                "match_id": match_id,
                "team": team,
                "goals": goals,
                "pass_att": pass_att,
                "pass_cmp": pass_cmp,
                "shots": random.randint(7, 18),
                "shots_on": random.randint(2, 8),
                "tackles": random.randint(12, 26),
                "interceptions": random.randint(6, 18),
                "blocks": random.randint(2, 10),
                "clears": random.randint(10, 30),
                "fouls": random.randint(8, 18),
                "corners": random.randint(2, 9),
            })

        # --- 선수 단위 기록 (우리 팀만 입력한다고 가정) ---
        for name, pos in SQUAD:
            if name in absent:
                continue  # 결장

            # 앞 11명은 주로 선발, 뒤 2명은 주로 교체
            started = 1 if SQUAD.index((name, pos)) < 11 else 0
            minutes = random.randint(70, 90) if started else random.randint(10, 30)

            lineups.append({
                "match_id": match_id, "player": name, "position": pos,
                "started": started, "minutes": minutes,
            })

            p_att = int(random.randint(20, 60) * minutes / 90)
            player_stats.append({
                "match_id": match_id,
                "player": name,
                "pass_att": p_att,
                "pass_cmp": int(p_att * random.uniform(0.72, 0.92)),
                "key_pass": random.randint(0, 3) if pos in ("MF", "FW") else 0,
                "shots": random.randint(0, 4) if pos == "FW" else random.randint(0, 1),
                "goals": 0,
                "assists": 0,
                "tackles": random.randint(0, 4),
                "interceptions": random.randint(0, 4),
                "duels_won": random.randint(1, 10),
            })

    _write("matches.csv", matches)
    _write("lineups.csv", lineups)
    _write("team_match_stats.csv", team_stats)
    _write("player_match_stats.csv", player_stats)
    print("샘플 데이터 생성 완료 (전부 가짜 숫자입니다)")


def _write(filename, rows):
    path = RAW / filename
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        # utf-8-sig: 엑셀에서 열 때 한글이 깨지지 않도록 BOM을 붙입니다
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.name}: {len(rows)}행")


if __name__ == "__main__":
    main()
