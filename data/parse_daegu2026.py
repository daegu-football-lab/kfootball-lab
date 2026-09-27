"""
data/raw/daegu2026/raw_pages.txt → 같은 폴더의 CSV 4개

raw_pages.txt 는 kleague.com 매치센터를 한 경기씩 열어 옮겨 적은 메모다.
메모를 고치면(오타 수정, 경기 추가) 이 파일을 다시 실행하면 된다:
    python data/parse_daegu2026.py

출력
  matches.csv          경기 1행
  lineups.csv          경기 x 선수 1행 (양 팀)
  team_match_stats.csv 경기 x 팀 1행 (양 팀)
  events.csv           경기 x 사건 1행 (골/도움/경고/퇴장/교체/유효슈팅)
"""
import csv
import re
import sys
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent / "raw" / "daegu2026"
SRC = RAW_DIR / "raw_pages.txt"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW_DIR
OUT.mkdir(parents=True, exist_ok=True)

# kleague.com 약칭 → 기존 team_season_stats.csv 와 같은 이름
TEAM = {
    "대구": "대구FC", "화성": "화성FC", "전남": "전남드래곤즈", "충남아산": "충남아산",
    "부산": "부산아이파크", "서울E": "서울이랜드", "김포": "김포FC", "수원FC": "수원FC",
    "천안": "천안시티", "경남": "경남FC", "수원": "수원삼성", "김해": "김해FC",
    "안산": "안산그리너스", "용인": "용인FC", "파주": "파주프런티어",
    "충북청주": "충북청주", "성남": "성남FC",
}
EVENT = {"G": "goal", "A": "assist", "도움": "assist", "O": "own_goal", "자책골": "own_goal",
         "U": "shot_on_target", "Y": "yellow", "R": "red", "S": "sub"}
STAT_KEYS = ["poss", "sh", "sot", "fo", "yc", "rc", "rc2", "ck", "fk", "off"]
RATING = re.compile(r"^\d{1,2}\.\d$")


def parse_blocks(text):
    blocks, cur = [], None
    for line in text.splitlines():
        if line.startswith("@@ "):
            gid, date, rnd, home, away = line[3:].split("|")
            cur = {"gid": int(gid), "date": date, "round": int(rnd[1:]),
                   "home": TEAM[home], "away": TEAM[away], "home_s": home, "away_s": away}
            blocks.append(cur)
        elif line.startswith("#"):
            key, _, val = line.partition(" ")
            cur[key[1:]] = val
    return blocks


def parse_starter(tok):
    """'97.은고이:2 7.6@5.0' → (번호, 이름, 주장, 골수표시, 평점, top%)"""
    left, _, top = tok.rpartition("@")
    left = left.replace(":", " ", 1)          # JS에서 첫 공백을 ':'로 바꿨던 것 복원
    num, _, rest = left.partition(".")
    parts = rest.split()
    rating = parts.pop() if parts and RATING.match(parts[-1]) else ""
    goals_badge = parts.pop() if parts and parts[-1].isdigit() else ""
    name = " ".join(parts)
    captain = name.endswith("(c)")
    return int(num), name.replace("(c)", ""), captain, rating, float(top)


def parse_bench(tok):
    """'99.마이사 폴:6.8' 또는 '1.고동민'"""
    num, _, rest = tok.partition(".")
    name, _, rating = rest.rpartition(":") if ":" in rest else (rest, "", "")
    captain = name.endswith("(c)")
    return int(num), name.replace("(c)", ""), captain, rating


def lines_to_positions(starters):
    """
    경기장 그림의 세로 위치(top%)로 포지션 줄을 나눈다. [추정]
    top이 클수록 우리 골문 쪽. 85 = GK.
    """
    outfield = sorted({s["top"] for s in starters if s["top"] < 80}, reverse=True)
    pos = {}
    for s in starters:
        if s["top"] >= 80:
            pos[s["name"]] = "GK"
        elif s["top"] == outfield[0]:
            pos[s["name"]] = "DF"
        elif s["top"] == outfield[-1]:
            pos[s["name"]] = "FW"
        else:
            pos[s["name"]] = "MF"
    formation = "-".join(str(sum(1 for s in starters if s["top"] == t)) for t in outfield)
    return pos, formation


def minute_parts(s):
    m = re.match(r"^(\d+)(?:\+(\d+))?", s)
    return int(m.group(1)), int(m.group(2) or 0), m.end()


def main():
    blocks = parse_blocks(SRC.read_text(encoding="utf-8"))
    matches, lineups, tstats, events = [], [], [], []
    problems = []

    for b in blocks:
        mid = f"2026-R{b['round']:02d}"
        att, stadium, weather, temp, kickoff, score = b["G"].split("|")
        hs, as_ = map(int, score.split("-"))
        matches.append({
            "match_id": mid, "game_id": b["gid"], "date": b["date"], "round": b["round"],
            "home_team": b["home"], "away_team": b["away"], "home_score": hs, "away_score": as_,
            "kickoff": kickoff[-5:], "weekday": kickoff.split("(")[1][0],
            "attendance": int(att), "stadium": stadium, "weather": weather,
            "temp_c": float(temp.replace("°C", "")),
        })

        # ---- 팀 기록 (양 팀) ----
        st = dict(kv.split(":") for kv in b["S"].split(";"))
        poss15 = b["P"].split(",")
        for side, team in (("home", b["home"]), ("away", b["away"])):
            i = 0 if side == "home" else 1
            row = {"match_id": mid, "team": team, "venue": "H" if side == "home" else "A",
                   "goals": hs if side == "home" else as_}
            names = {"poss": "possession", "sh": "shots", "sot": "shots_on", "fo": "fouls",
                     "yc": "yellow", "rc": "red", "rc2": "red_2nd_yellow", "ck": "corners",
                     "fk": "free_kicks", "off": "offsides"}
            for k in STAT_KEYS:
                row[names[k]] = int(st[k].split("-")[i]) if k in st else ""
            for j, label in enumerate(["p00_15", "p15_30", "p30_45", "p45_60", "p60_75", "p75_90"]):
                v = float(poss15[j])
                row[label] = round(v if side == "home" else 100 - v, 2)
            tstats.append(row)

        # ---- 명단 ----
        roster = {}   # (team) -> {name: dict}
        for side, team, sk, bk in (("home", b["home"], "H1", "H2"), ("away", b["away"], "A1", "A2")):
            starters = []
            for tok in b[sk].split(","):
                num, name, cap, rating, top = parse_starter(tok)
                starters.append({"num": num, "name": name, "cap": cap, "rating": rating, "top": top})
            pos, formation = lines_to_positions(starters)
            if len(starters) != 11:
                problems.append(f"{mid} {team} 선발 {len(starters)}명")
            roster[team] = {}
            for s in starters:
                roster[team][s["name"]] = {**s, "started": 1, "position": pos[s["name"]],
                                           "formation": formation}
            for tok in b[bk].split(","):
                num, name, cap, rating = parse_bench(tok)
                roster[team][name] = {"num": num, "name": name, "cap": cap, "rating": rating,
                                      "started": 0, "position": "", "formation": formation}

        # ---- 사건 ----
        half = 1
        for seq, ev in enumerate(filter(None, b["T"].split(";")), 1):
            base, added, end = minute_parts(ev)
            body = ev[end:]
            code = next(c for c in sorted(EVENT, key=len, reverse=True) if body.startswith(c))
            detail = body[len(code):]
            etype = EVENT[code]
            if base > 45 or (base == 45 and added == 0 and etype == "sub"):
                half = 2
            row = {"match_id": mid, "seq": seq, "half": half, "minute": base, "added": added,
                   "type": etype, "team": "", "number": "", "player": "", "player_out": ""}
            if etype == "sub":
                pin, pout = detail.split(">")
                team = next((t for t, r in roster.items() if pin in r and pout in r), "")
                if not team:
                    problems.append(f"{mid} 교체 팀 판별 실패: {ev}")
                row.update(team=team, player=pin, player_out=pout)
            else:
                m = re.match(r"^(.+?)(\d+),(.+)$", detail)
                if not m:
                    problems.append(f"{mid} 사건 해석 실패: {ev}")
                    continue
                row.update(team=TEAM[m.group(1)], number=int(m.group(2)), player=m.group(3))
            events.append(row)

        # ---- 출전 시간 계산 (추가시간은 무시하고 90분 기준) ----
        for team, r in roster.items():
            for p in r.values():
                p["in"] = 0 if p["started"] else None
                p["out"] = None
        for e in (e for e in events if e["match_id"] == mid):
            if e["type"] == "sub":
                r = roster[e["team"]]
                r[e["player"]]["in"] = e["minute"]
                r[e["player_out"]]["out"] = e["minute"]
                if not r[e["player"]]["position"]:
                    r[e["player"]]["position"] = r[e["player_out"]]["position"]
                    r[e["player"]]["pos_from_replaced"] = 1
            elif e["type"] == "red":
                roster[e["team"]][e["player"]]["out"] = e["minute"]
        for team, r in roster.items():
            for p in r.values():
                played = p["in"] is not None
                minutes = (min(p["out"] if p["out"] is not None else 90, 90) - p["in"]) if played else 0
                goals = sum(1 for e in events if e["match_id"] == mid and e["type"] == "goal"
                            and e["team"] == team and e["player"] == p["name"])
                assists = sum(1 for e in events if e["match_id"] == mid and e["type"] == "assist"
                              and e["team"] == team and e["player"] == p["name"])
                lineups.append({
                    "match_id": mid, "team": team, "number": p["num"], "player": p["name"],
                    "position": p["position"], "pos_estimated_from_sub": p.get("pos_from_replaced", 0),
                    "started": p["started"], "played": int(played), "minutes": max(minutes, 0),
                    "sub_in_minute": "" if p["started"] or not played else p["in"],
                    "sub_out_minute": "" if p["out"] is None else p["out"],
                    "goals": goals, "assists": assists, "captain": int(p["cap"]),
                    "rating": p["rating"], "formation": p["formation"] if p["started"] else "",
                })

        # ---- 교차검증: 골 사건 수 = 스코어 ----
        for team, score in ((b["home"], hs), (b["away"], as_)):
            other = b["away"] if team == b["home"] else b["home"]
            g = sum(1 for e in events if e["match_id"] == mid and
                    ((e["type"] == "goal" and e["team"] == team) or
                     (e["type"] == "own_goal" and e["team"] == other)))
            if g != score:
                problems.append(f"{mid} {team} 골 사건 {g} != 스코어 {score}")
            y = sum(1 for e in events if e["match_id"] == mid and e["type"] == "yellow" and e["team"] == team)
            trow = next(t for t in tstats if t["match_id"] == mid and t["team"] == team)
            # 통계의 '경고'에는 경고누적 퇴장의 두 번째 경고도 들어 있다 (사건 목록에선 '퇴장' 1건)
            ys = trow["yellow"] - (trow["red_2nd_yellow"] or 0)
            if y != ys:
                problems.append(f"{mid} {team} 경고 사건 {y} != 통계 {ys}")

    def write(name, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write("matches.csv", matches)
    write("lineups.csv", lineups)
    write("team_match_stats.csv", tstats)
    write("events.csv", events)
    print(f"경기 {len(matches)} / 명단 {len(lineups)} / 팀기록 {len(tstats)} / 사건 {len(events)}")
    print("문제:" if problems else "문제 없음")
    for p in problems:
        print("  -", p)


if __name__ == "__main__":
    main()
