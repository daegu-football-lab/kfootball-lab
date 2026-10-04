"""직전 홈경기 결과 vs 다음 홈경기 관중 변화 (2026 K리그2).

입력(원시, gitignore): data/raw/attendance2026/_page_rows_20260927.txt  (kleague.com 관중현황 1회 조회)
                      data/raw/daegu2026/matches.csv                    (대구: 킥오프·날씨 포함)
출력:
  data/raw/attendance2026/top6_home.csv   원시 행 (공개 금지)
  output/attendance/daegu_home_prev.csv   대구 홈 13경기 표 (경기별 → 공개 전 검토)
  output/attendance/prev_summary.csv      집계값만 (공개 가능)
해석은 쓰지 않는다. 숫자만 만든다.
"""
import csv, datetime as dt, statistics as st
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data/raw/attendance2026"
OUT = ROOT / "output/attendance"
TEAMS = ["수원", "수원FC", "서울E", "대구", "화성", "부산"]
WD = "월화수목금토일"


def load_page_rows():
    rows = []
    for line in open(RAW / "_page_rows_20260927.txt", encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        d, h, a, s, att, af, _w, venue = line.strip().split(",")
        date = dt.date(2026, int(d[:2]), int(d[2:]))
        hs, as_ = map(int, s.split(":"))
        rows.append(dict(date=date, home=h, away=a, hs=hs, as_=as_, att=int(att),
                         away_fans=af, weekday=WD[date.weekday()], venue=venue))
    return sorted(rows, key=lambda r: (r["home"], r["date"]))


def result(hs, as_):
    return "승" if hs > as_ else ("무" if hs == as_ else "패")


def with_prev(games):
    """각 홈경기에 '직전 홈경기' 결과·득점과 관중 변화를 붙인다 (첫 경기는 비교 없음)."""
    out = []
    for i, g in enumerate(games):
        p = games[i - 1] if i else None
        out.append(dict(g, res=result(g["hs"], g["as_"]),
                        prev_res=result(p["hs"], p["as_"]) if p else "",
                        prev_gf=p["hs"] if p else "",
                        delta=g["att"] - p["att"] if p else "",
                        gap_days=(g["date"] - p["date"]).days if p else ""))
    return out


def summarize(label, games):
    g = [x for x in games if x["prev_res"]]
    groups = {
        "직전 홈 승리": [x["delta"] for x in g if x["prev_res"] == "승"],
        "직전 홈 비승리": [x["delta"] for x in g if x["prev_res"] != "승"],
        "직전 홈 2골 이상": [x["delta"] for x in g if x["prev_gf"] >= 2],
        "직전 홈 2골 미만": [x["delta"] for x in g if x["prev_gf"] < 2],
    }
    return [[label, k, len(v), round(st.mean(v)) if v else "", round(st.median(v)) if v else ""]
            for k, v in groups.items()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_page_rows()

    with open(RAW / "top6_home.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["date", "round", "home", "away", "home_score", "away_score", "attendance",
                    "kickoff", "weekday", "weather", "game_id", "away_fans_col", "venue"])
        for r in rows:  # 관중현황 페이지에 없는 round/kickoff/weather/game_id 는 빈칸
            w.writerow([r["date"], "", r["home"], r["away"], r["hs"], r["as_"], r["att"],
                        "", r["weekday"], "", "", r["away_fans"], r["venue"]])

    # 대구: 기존 matches.csv 기준 (킥오프·날씨 포함). 관중현황 페이지 값과 교차검증.
    dg = []
    for x in csv.DictReader(open(ROOT / "data/raw/daegu2026/matches.csv", encoding="utf-8-sig")):
        if "대구" in x["home_team"]:
            dg.append(dict(date=dt.date.fromisoformat(x["date"]), round=x["round"], away=x["away_team"],
                           hs=int(x["home_score"]), as_=int(x["away_score"]), att=int(x["attendance"]),
                           kickoff=x["kickoff"], weekday=x["weekday"], weather=x["weather"]))
    dg.sort(key=lambda r: r["date"])
    page = {(r["date"], r["hs"], r["as_"], r["att"]) for r in rows if r["home"] == "대구"}
    mism = [str(r["date"]) for r in dg if (r["date"], r["hs"], r["as_"], r["att"]) not in page]
    print(f"대구 홈 {len(dg)}경기, 관중현황 페이지와 불일치: {mism or '없음'}")

    dgp = with_prev(dg)
    cols = ["date", "round", "weekday", "kickoff", "weather", "away", "hs", "as_", "res", "att",
            "prev_res", "prev_gf", "delta", "gap_days"]
    with open(OUT / "daegu_home_prev.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(dgp)

    summary = summarize("대구", dgp)
    allp = []
    for t in TEAMS:
        tp = with_prev([r for r in rows if r["home"] == t])
        allp += tp
        if t != "대구":
            summary += summarize(t, tp)
    summary += summarize("6팀 합산", allp)
    # 민감도: 원정팀 열(원정 관중 추정)을 뺀 '홈 측' 관중으로 다시
    home_side = [dict(r, att=r["att"] - int(r["away_fans"] or 0)) for r in rows]
    hp = []
    for t in TEAMS:
        hp += with_prev([r for r in home_side if r["home"] == t])
    summary += summarize("6팀 합산(원정석 제외, 추정)", hp)

    with open(OUT / "prev_summary.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["team", "group", "n", "mean_delta", "median_delta"]); w.writerows(summary)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
