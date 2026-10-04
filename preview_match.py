"""
3편(대구 vs 다음 상대 예고)용 숫자 표 + 카드 1장을 만듭니다.

실행:  python preview_match.py
결과:  output/preview/preview_<상대>.md   (글에 옮길 숫자, 공개 안 함)
       output/charts/card_03_split.png    (블로그 첫 카드)

설계 메모
- 숫자는 전부 data/raw의 CSV에서 다시 계산합니다. 발행 직전(10/25 무렵)에
  경기 기록과 team_season_stats.csv만 갱신하고 이 파일을 다시 돌리면 됩니다.
- "상위권"은 기준일 순위표에서 대구를 뺀 상위 5팀입니다. 순위가 바뀌면 자동으로 바뀝니다.
  (주의: 경기 당시 순위가 아니라 '지금' 순위로 나눕니다 → 글의 한계 절에 적을 것)
- 해석 문장은 만들지 않습니다. 숫자만.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.config import RAW_DIR, OUTPUT_DIR, CHART_DIR, MY_TEAM, DATA_AS_OF, DATA_AS_OF_NOTE
from src import card_style as cs

OPPONENT = "수원삼성"      # 다음 예고 상대. 다른 경기 예고 때 여기만 바꿉니다
TOP_N = 6                 # 상위권 = 순위표 상위 6팀(PO권)에서 대구 제외
DAEGU_DIR = RAW_DIR / "daegu2026"


def read_csv(path):
    # utf-8-sig: 엑셀이 붙이는 BOM(파일 앞 보이지 않는 표시)을 자동 제거
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if not r[next(iter(r))].startswith("#")]


def standings():
    """K리그 순위 규칙(대회요강 제30조): 승점 → 다득점 → 득실차."""
    rows = read_csv(RAW_DIR / "team_season_stats.csv")
    for r in rows:
        for k in ("matches", "wins", "draws", "losses", "goals", "goals_against", "points"):
            r[k] = int(r[k])
    rows.sort(key=lambda r: (r["points"], r["goals"], r["goals"] - r["goals_against"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def daegu_matches():
    """대구 경기마다 (상대, 홈/원정, 득점, 실점, 결과)."""
    out = []
    for m in read_csv(DAEGU_DIR / "matches.csv"):
        home = m["home_team"] == MY_TEAM
        gf, ga = int(m["home_score"]), int(m["away_score"])
        if not home:
            gf, ga = ga, gf
        out.append({**m, "opp": m["away_team"] if home else m["home_team"], "is_home": home,
                    "gf": gf, "ga": ga, "pts": 3 if gf > ga else (1 if gf == ga else 0)})
    return out


def summary(games):
    n = len(games)
    if n == 0:
        return {"n": 0}
    w = sum(g["pts"] == 3 for g in games); d = sum(g["pts"] == 1 for g in games)
    return {"n": n, "w": w, "d": d, "l": n - w - d,
            "gf": sum(g["gf"] for g in games), "ga": sum(g["ga"] for g in games),
            "ppg": sum(g["pts"] for g in games) / n}


def fmt(s):
    return (f"{s['n']}경기 {s['w']}승 {s['d']}무 {s['l']}패, {s['gf']}득 {s['ga']}실, "
            f"경기당 승점 {s['ppg']:.2f}, 경기당 득점 {s['gf']/s['n']:.2f} / 실점 {s['ga']/s['n']:.2f}")


def h2h_stats(match_id):
    rows = [r for r in read_csv(DAEGU_DIR / "team_match_stats.csv") if r["match_id"] == match_id]
    return {r["team"]: r for r in rows}


def draw_card(split, top_names, as_of_text):
    rows = [  # (라벨, 요약, 강조 여부)
        (f"상위 5팀 상대", split["top"], True),
        (f"나머지 팀 상대", split["rest"], False),
        (f"전체", split["all"], False),
    ]
    fig = cs.new_card(
        "K리그2 승격 경쟁", "③", f"{OPPONENT}전 예고",
        f"대구 경기당 승점: 상위 5팀 상대 {split['top']['ppg']:.2f} · 나머지 {split['rest']['ppg']:.2f}",
        "기준일 순위표 상위 5팀(대구 제외)과 치른 경기와 나머지 경기를 나눠 경기당 승점을 냈다 · 막대가 길수록 승점이 많다",
    )
    ax = fig.add_axes([0.22, 0.25, 0.60, 0.42], facecolor=cs.SURFACE)
    n = len(rows)
    for i, (label, s, focus) in enumerate(rows):
        y = n - 1 - i
        ax.barh(y, 3, height=0.5, color=cs.TRACK, zorder=1)          # 최대 3점 트랙
        ax.barh(y, s["ppg"], height=0.5, color=cs.FOCUS if focus else cs.MUTED, zorder=2)
        weight = "bold" if focus else "normal"
        ax.text(-0.08, y + 0.08, label, ha="right", va="center", fontsize=20, color=cs.TEXT_1, weight=weight)
        ax.text(-0.08, y - 0.22, f"{s['n']}경기 · {s['w']}승 {s['d']}무 {s['l']}패",
                ha="right", va="center", fontsize=14, color=cs.TEXT_2)
        ax.text(s["ppg"] + 0.05, y, f"{s['ppg']:.2f}", va="center", fontsize=20, color=cs.TEXT_1, weight=weight)
    ax.set_xlim(0, 3); ax.set_ylim(-0.6, n - 0.4)
    ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["0", "1 (매 경기 무)", "2", "3 (매 경기 승)"],
                                                   fontsize=13, color=cs.TEXT_3)
    ax.tick_params(axis="x", length=0, pad=8); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.text(0.22, 0.175, "상위 5팀: " + ", ".join(top_names), fontsize=14, color=cs.TEXT_2)
    cs.add_footer(fig, as_of_text + " · 상위권 구분은 기준일 순위 기준(경기 당시 순위 아님)")
    out = CHART_DIR / "card_03_split.png"
    fig.savefig(out, facecolor=cs.SURFACE)
    return out


def main():
    table = standings()
    by_team = {r["team"]: r for r in table}
    top_names = [r["team"] for r in table[:TOP_N] if r["team"] != MY_TEAM][:5]
    games = daegu_matches()
    y, mth, day = DATA_AS_OF.split("-")
    as_of_text = f"기준: {y}년 {int(mth)}월 {int(day)}일 ({DATA_AS_OF_NOTE})"

    split = {"all": summary(games),
             "top": summary([g for g in games if g["opp"] in top_names]),
             "rest": summary([g for g in games if g["opp"] not in top_names]),
             "home": summary([g for g in games if g["is_home"]])}

    L = [f"# {MY_TEAM} vs {OPPONENT} 예고용 숫자", "", f"> {as_of_text}", "",
         "## 1. 순위표 (다득점 규칙 반영)"]
    for t in (OPPONENT, MY_TEAM):
        r = by_team[t]
        L.append(f"- {t}: {r['rank']}위, {r['matches']}경기 {r['points']}점 ({r['wins']}승 {r['draws']}무 {r['losses']}패), "
                 f"{r['goals']}득 {r['goals_against']}실, 경기당 득점 {r['goals']/r['matches']:.2f} / 실점 {r['goals_against']/r['matches']:.2f}, "
                 f"경기당 승점 {r['points']/r['matches']:.2f}")
    second = table[1]
    L.append(f"- 참고 2위 {second['team']}: {second['points']}점 ({second['matches']}경기) → 대구와 {second['points'] - by_team[MY_TEAM]['points']}점 차")

    L += ["", f"## 2. 올해 맞대결 ({OPPONENT})"]
    for g in [g for g in games if g["opp"] == OPPONENT]:
        st = h2h_stats(g["match_id"])
        L.append(f"- {g['date']} R{g['round']} {g['home_team']} {g['home_score']}:{g['away_score']} {g['away_team']} "
                 f"(관중 {g['attendance']})")
        for t in (MY_TEAM, OPPONENT):
            s = st.get(t)
            if s:
                L.append(f"  - {t}: 점유율 {s['possession']}%, 슈팅 {s['shots']}, 유효슈팅 {s['shots_on']}, "
                         f"코너킥 {s['corners']}, 파울 {s['fouls']}, 경고 {s['yellow']}")

    L += ["", "## 3. 대구 성적 나누기 (카드 데이터)",
          f"- 상위 5팀 = {', '.join(top_names)}",
          f"- 상위 5팀 상대: {fmt(split['top'])}",
          f"- 나머지 상대: {fmt(split['rest'])}",
          f"- 전체: {fmt(split['all'])}",
          f"- 홈 전체: {fmt(split['home'])}",
          "", "### 상위 5팀 상대 경기 목록"]
    for g in [g for g in games if g["opp"] in top_names]:
        L.append(f"- {g['date']} R{g['round']} {'홈' if g['is_home'] else '원정'} vs {g['opp']} {g['gf']}:{g['ga']}")

    card = draw_card(split, top_names, as_of_text)
    out_dir = OUTPUT_DIR / "preview"; out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"preview_{OPPONENT}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"숫자: {md}\n카드: {card}")


if __name__ == "__main__":
    main()
