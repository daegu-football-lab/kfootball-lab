"""
선수 탭·On/Off 탭용 실제 기록 → site/data/players.js (+ players.json)

입력 (비공개 원시 데이터, data/raw/daegu2026/ — parse_daegu2026.py 가 만든 CSV)
  matches.csv   경기 1행
  lineups.csv   경기 x 선수 1행 (출전·선발·출전분·골·도움·포지션)
  events.csv    경기 x 사건 1행 (경고·퇴장)

출력 (공개 — 선수별 '시즌 합계'만. 경기별 원시 행은 내보내지 않음)
  players  선수별 출전·선발·출전분·골·도움·공격포인트·경고·퇴장, 90분당 환산
  onoff    출전한 경기 / 결장한 경기의 팀 경기당 승점·득점·실점
  teams    리그 팀 비교 표 (기존 analyze.team_season_table 그대로)
  matches  대구 경기 결과 (날짜·상대·스코어만)

왜 따로 만들었나
  기존 export_site_json 은 data/raw/player_match_stats.csv(샘플)를 쓰는 구조였습니다.
  매치센터에서 옮겨 적은 실제 기록(daegu2026)이 30경기 쌓였으므로, 그 기록으로 같은 모양의
  파일을 만들어 사이트 코드를 거의 그대로 쓰게 했습니다.

데이터 한계 (사이트에도 같은 문구를 보여 줌)
  - 출전분은 교체 시각 기준이며 추가시간을 넣지 않습니다(한 경기 최대 90분).
  - 패스·태클 같은 세부 기록은 매치센터 화면에 없어 다루지 않습니다.
  - 평점(연맹 자체 점수)은 계산식이 공개되지 않아 이번에는 싣지 않습니다.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date

from src import analyze, config, load

RAW = config.RAW_DIR / "daegu2026"
MIN_GROUP = 5  # On/Off 한쪽 경기 수가 이보다 적으면 경고 문구를 붙임
MIN_SHOW = 3   # On/Off 목록에 올리는 최소 경기 수(출전·결장 양쪽 모두)


def available() -> bool:
    return all((RAW / f).exists() for f in ("matches.csv", "lineups.csv", "events.csv"))


def _read(name: str) -> list[dict]:
    with open(RAW / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _per90(value: int, minutes: int) -> float:
    return round(value * 90 / minutes, 2) if minutes else 0.0


def build_players(lineups: list[dict], events: list[dict], team: str) -> list[dict]:
    """선수별 시즌 합계. 1분이라도 뛴 경기만 '출전'으로 셉니다."""
    acc: dict[str, dict] = defaultdict(lambda: Counter())
    positions: dict[str, Counter] = defaultdict(Counter)
    for r in lineups:
        if r["team"] != team:
            continue
        name = r["player"]
        if r["position"]:
            positions[name][r["position"]] += 1
        if r["played"] != "1":
            continue
        a = acc[name]
        a["출전경기"] += 1
        a["선발"] += int(r["started"])
        a["출전시간"] += int(r["minutes"] or 0)
        a["골"] += int(r["goals"] or 0)
        a["도움"] += int(r["assists"] or 0)

    for e in events:
        if e["team"] == team and e["player"] in acc:
            if e["type"] == "yellow":
                acc[e["player"]]["경고"] += 1
            elif e["type"] == "red":
                acc[e["player"]]["퇴장"] += 1

    out = []
    for name, a in acc.items():
        mins = a["출전시간"]
        pts = a["골"] + a["도움"]
        out.append({
            "player": name,
            # 가장 많이 선 자리. 교체로만 뛴 선수는 비어 있을 수 있음
            "포지션": positions[name].most_common(1)[0][0] if positions[name] else "",
            "출전경기": a["출전경기"], "선발": a["선발"], "출전시간": mins,
            "골": a["골"], "도움": a["도움"], "공격포인트": pts,
            "경고": a["경고"], "퇴장": a["퇴장"],
            "골_per90": _per90(a["골"], mins), "도움_per90": _per90(a["도움"], mins),
            "공격포인트_per90": _per90(pts, mins),
        })
    return sorted(out, key=lambda p: -p["출전시간"])


def _team_result(m: dict, team: str) -> tuple[int, int]:
    hs, as_ = int(m["home_score"]), int(m["away_score"])
    return (hs, as_) if m["home_team"] == team else (as_, hs)


def _summary(games: list[tuple[int, int]]) -> dict:
    n = len(games)
    pts = sum(3 if f > a else 1 if f == a else 0 for f, a in games)
    return {"경기수": n,
            "경기당 승점": round(pts / n, 2) if n else 0,
            "경기당 득점": round(sum(f for f, _ in games) / n, 2) if n else 0,
            "경기당 실점": round(sum(a for _, a in games) / n, 2) if n else 0}


def build_onoff(matches: list[dict], lineups: list[dict], team: str) -> dict:
    """출전 경기 vs 결장 경기의 팀 결과. 인과가 아니라 '같이 나타난 것'만 셉니다."""
    result = {m["match_id"]: _team_result(m, team) for m in matches}
    played_in: dict[str, set] = defaultdict(set)
    for r in lineups:
        if r["team"] == team and r["played"] == "1":
            played_in[r["player"]].add(r["match_id"])

    out = {}
    for name, ids in sorted(played_in.items(), key=lambda kv: -len(kv[1])):
        on = [result[i] for i in result if i in ids]
        off = [result[i] for i in result if i not in ids]
        if len(on) < MIN_SHOW or len(off) < MIN_SHOW:
            continue
        s_on, s_off = _summary(on), _summary(off)
        small = min(len(on), len(off))
        out[name] = {
            "player": name, "on": s_on, "off": s_off,
            "diff": {k: round(s_on[k] - s_off[k], 2) for k in s_on if k != "경기수"},
            "warning": (f"한쪽 그룹이 {small}경기뿐입니다. 우연일 가능성이 크니 '경향' 수준으로만 보세요."
                        if small < MIN_GROUP else ""),
        }
    return out


def export() -> str:
    team = config.MY_TEAM
    matches, lineups, events = _read("matches.csv"), _read("lineups.csv"), _read("events.csv")

    data = load.load_all()  # 팀 비교 표(team_season_stats.csv)는 기존 함수를 그대로 씀
    team_table = analyze.team_season_table(data)

    match_rows = []
    for m in matches:
        gf, ga = _team_result(m, team)
        home = m["home_team"] == team
        match_rows.append({"match_id": m["match_id"], "date": m["date"], "round": int(m["round"]),
                           "opponent": m["away_team"] if home else m["home_team"],
                           "venue": "홈" if home else "원정", "gf": gf, "ga": ga,
                           "points": 3 if gf > ga else 1 if gf == ga else 0})

    payload = {
        "meta": {
            "team": team, "season": config.SEASON,
            "generated_at": date.today().isoformat(),
            "as_of": config.DATA_AS_OF,
            "is_sample": False,
            "team_is_real": data.get("team_season") is not None,
            "players_source": "K리그 매치센터 경기별 기록을 한 경기씩 옮겨 적음",
            "players_matches": len(matches),
            "players_note": "출전분은 교체 시각 기준(추가시간 제외, 경기당 최대 90분). 자책골은 선수 골에 넣지 않음.",
        },
        "players": build_players(lineups, events, team),
        "teams": team_table.to_dict(orient="records"),
        "matches": match_rows,
        "onoff": build_onoff(matches, lineups, team),
    }

    js = config.SITE_DATA_DIR / "players.js"
    js.write_text("// 선수·On/Off·팀 비교 데이터 (python run.py players 로 다시 만듭니다. 손으로 고치지 마세요)\n"
                  "window.KFL_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
    (config.SITE_DATA_DIR / "players.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  선수 {len(payload['players'])}명 / On·Off {len(payload['onoff'])}명 / "
          f"경기 {len(match_rows)} -> {js}")
    return str(js)


if __name__ == "__main__":
    export()
