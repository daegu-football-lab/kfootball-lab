"""
[분석 #5](대구 vs 다음 상대 예고)용 숫자 표 + 카드 1장 + 원고 붙여넣기용 숫자 문장을 만듭니다.

실행:  python preview_match.py
결과:  output/preview/preview_<상대>.md   (글에 옮길 숫자, 공개 안 함)
       output/charts/card_03_split.png    (블로그 첫 카드)

설계 메모
- 숫자는 전부 data/raw의 CSV에서 다시 계산합니다. 발행 직전(10/25 무렵)에
  경기 기록과 team_season_stats.csv만 갱신하고 이 파일을 다시 돌리면 됩니다.
- "상위권"은 기준일 순위표에서 대구를 뺀 상위 5팀입니다. 순위가 바뀌면 자동으로 바뀝니다.
  (주의: 경기 당시 순위가 아니라 '지금' 순위로 나눕니다 → 글의 한계 절에 적을 것)
- 해석 문장은 만들지 않습니다. 숫자만.
- 10/13 추가: 감독별 나누기, 9/30 순위와 비교 표, 남은 일정 확인, 원고 [숫자:갱신] 자리에
  그대로 붙일 문장(원고와 같은 문장 틀에 숫자만 바꿔 넣음).
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.config import RAW_DIR, OUTPUT_DIR, CHART_DIR, SITE_DATA_DIR, MY_TEAM, DATA_AS_OF, DATA_AS_OF_NOTE
from src import card_style as cs

OPPONENT = "수원삼성"      # 다음 예고 상대. 다른 경기 예고 때 여기만 바꿉니다
TOP_N = 6                 # 상위권 = 순위표 상위 6팀(PO권)에서 대구 제외
DAEGU_DIR = RAW_DIR / "daegu2026"

# 비교 기준 순위표: [분석 #2]가 쓴 9/30(27R 종료) 순위. 공개 금지 폴더(data/raw)에 둔다.
SNAPSHOT_CSV = RAW_DIR / "team_season_stats_27R.csv"
SNAPSHOT_LABEL = "9/30(27R)"
# 최성용 감독 선임일(매일신문 4/26 보도 기준, 64번 문서). 이 날짜 전 경기 = 김병수 감독 시절
COACH_CHANGE = "2026-04-20"
# 원고 표기(짧은 이름). 목록에 없으면 "OO FC" → "OO"로 줄이고, 수원FC는 그대로 둔다
SHORT_NAME = {"부산아이파크": "부산", "수원FC": "수원FC"}


def read_csv(path):
    # utf-8-sig: 엑셀이 붙이는 BOM(파일 앞 보이지 않는 표시)을 자동 제거
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if not r[next(iter(r))].startswith("#")]


def standings(path=RAW_DIR / "team_season_stats.csv"):
    """K리그 순위 규칙(대회요강 제30조): 승점 → 다득점 → 득실차."""
    rows = read_csv(path)
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
        "[분석", "#5]", f"{OPPONENT}전 예고",
        f"대구 경기당 승점: 상위 5팀 상대 {split['top']['ppg']:.2f} · 나머지 {split['rest']['ppg']:.2f}",
        "상위 5팀(대구 제외)과 나머지 팀으로 나눈 경기당 승점 · 막대가 길수록 승점이 많다",
        sub_size=26,   # 블로그 본문 폭에서 읽히는 크기
    )
    ax = fig.add_axes([0.26, 0.27, 0.60, 0.40], facecolor=cs.SURFACE)
    n = len(rows)
    for i, (label, s, focus) in enumerate(rows):
        y = n - 1 - i
        ax.barh(y, 3, height=0.5, color=cs.TRACK, zorder=1)          # 최대 3점 트랙
        ax.barh(y, s["ppg"], height=0.5, color=cs.FOCUS if focus else cs.MUTED, zorder=2)
        weight = "bold" if focus else "normal"
        ax.text(-0.08, y + 0.12, label, ha="right", va="center", fontsize=28, color=cs.TEXT_1, weight=weight)
        ax.text(-0.08, y - 0.26, f"{s['n']}경기 · {s['w']}승 {s['d']}무 {s['l']}패",
                ha="right", va="center", fontsize=21, color=cs.TEXT_2)
        ax.text(s["ppg"] + 0.05, y, f"{s['ppg']:.2f}", va="center", fontsize=30, color=cs.TEXT_1, weight=weight)
    ax.set_xlim(0, 3); ax.set_ylim(-0.6, n - 0.4)
    ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["0", "1 (매 경기 무)", "2", "3 (매 경기 승)"],
                                                   fontsize=20, color=cs.TEXT_2)
    ax.tick_params(axis="x", length=0, pad=8); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.text(0.26, 0.165, "상위 5팀: " + ", ".join(top_names), fontsize=21, color=cs.TEXT_2)
    cs.add_footer(fig, as_of_text, size=21)   # 상위권 구분 설명은 본문 한계 장에 있음
    out = CHART_DIR / "card_03_split.png"
    fig.savefig(out, facecolor=cs.SURFACE)
    return out

# ---------------------------------------------------------------------------
# 원고 문장용 작은 도구
# ---------------------------------------------------------------------------
_BATCHIM_DIGIT = set("013678")   # 숫자 끝소리: 영·일·삼·육·칠·팔은 받침 있음


def _has_batchim(text):
    """마지막 글자에 받침이 있는지. 숫자는 읽는 소리 기준."""
    ch = text[-1]
    if ch.isdigit():
        return ch in _BATCHIM_DIGIT
    code = ord(ch) - 0xAC00
    return 0 <= code <= 11171 and code % 28 != 0


def ida(t):      # 2.35다 / 2.30이다
    return t + ("이다" if _has_batchim(t) else "다")


def ieotda(t):   # 0.67이었다 / 0.75였다
    return t + ("이었다" if _has_batchim(t) else "였다")


def eun(t):      # 수원삼성은 / 대구는
    return t + ("은" if _has_batchim(t) else "는")


def short(team):
    if team in SHORT_NAME:
        return SHORT_NAME[team]
    return team[:-2] if team.endswith("FC") else team


def slash_date(d):    # 2026-08-01 → 8/1
    _, m, dd = d.split("-")
    return f"{int(m)}/{int(dd)}"


def kr_date(d):       # 2026-08-01 → 8월 1일
    _, m, dd = d.split("-")
    return f"{int(m)}월 {int(dd)}일"


def wdl(s):
    return f"{s['w']}승 {s['d']}무 {s['l']}패"


def remaining_daegu_fixtures():
    """site/data/fixtures.js(공개 일정표)에서 기준일 이후 대구 경기."""
    text = (SITE_DATA_DIR / "fixtures.js").read_text(encoding="utf-8")
    data = json.loads(text[text.index("=") + 1:].strip().rstrip(";"))
    games = next(v for v in data.values() if isinstance(v, list))
    return [g for g in games if MY_TEAM in (g["home"], g["away"]) and g["date"] > DATA_AS_OF]


def extra_sections(table, games, top_names):
    """4~7절: 감독별 / 9월 30일 순위와 비교 / 남은 일정 / 원고 붙여넣기용 문장."""
    by_team = {r["team"]: r for r in table}
    me, opp, second = by_team[MY_TEAM], by_team[OPPONENT], table[1]
    top6 = [r["team"] for r in table[:TOP_N]]
    top_games = [g for g in games if g["opp"] in top_names]
    rest_games = [g for g in games if g["opp"] not in top_names]
    home_games = [g for g in games if g["is_home"]]
    s_top, s_rest, s_home = summary(top_games), summary(rest_games), summary(home_games)
    s_top_home = summary([g for g in top_games if g["is_home"]])
    before = [g for g in top_games if g["date"] < COACH_CHANGE]
    after = [g for g in top_games if g["date"] >= COACH_CHANGE]
    y, m, d = DATA_AS_OF.split("-")
    L = []

    # 4. 감독별 (67번 ④C 문구용)
    L += ["", "## 4. 상위 5팀 상대, 감독별 (선임일 " + COACH_CHANGE + " 기준)"]
    for label, gs in (("김병수", before), ("최성용", after)):
        if gs:
            L.append(f"- {label}: {fmt(summary(gs))} ({slash_date(gs[0]['date'])}~{slash_date(gs[-1]['date'])})")
    after_all = summary([g for g in games if g["date"] >= COACH_CHANGE])
    L.append(f"- 참고 최성용 체제 전체: {fmt(after_all)}")
    unbeaten = [t for t in top_names
                if any(g["opp"] == t for g in top_games) and all(g["pts"] >= 1 for g in top_games if g["opp"] == t)]
    L.append(f"- 상위 5팀 중 올해 대구가 진 적 없는 팀: {', '.join(unbeaten) or '없음'}")

    # 5. 9/30 순위와 비교 (신규 절 표 B안)
    snap = {r["team"]: r for r in standings(SNAPSHOT_CSV)}
    snap_top5 = [r["team"] for r in standings(SNAPSHOT_CSV)[:TOP_N] if r["team"] != MY_TEAM][:5]
    L += ["", f"## 5. 상위 6팀, {SNAPSHOT_LABEL} → 지금 (바뀐 순위만 굵게)", "",
          f"| 순위 | 팀 | 경기 | 승점 | {SNAPSHOT_LABEL} 순위 | {SNAPSHOT_LABEL} 승점 |",
          "|---|---|---|---|---|---|"]
    for r in table[:TOP_N]:
        sr = snap.get(r["team"])
        rank = f"**{r['rank']}**" if sr and sr["rank"] != r["rank"] else str(r["rank"])
        L.append(f"| {rank} | {short(r['team'])} | {r['matches']} | {r['points']} | "
                 f"{sr['rank'] if sr else '-'} | {sr['points'] if sr else '-'} |")
    if set(snap_top5) != set(top_names):
        L.append(f"- ⚠️ 상위 5팀 구성이 바뀜: {SNAPSHOT_LABEL} {', '.join(snap_top5)} → 지금 {', '.join(top_names)}"
                 " → 원고 3장 문장·표·한계 절 다시 읽기")
    else:
        L.append(f"- 상위 5팀 구성은 {SNAPSHOT_LABEL}와 같음")

    # 6. 남은 일정 (1장 '남은 경기 중 상위 6팀은 이 한 경기' 문장 확인)
    L += ["", "## 6. 대구 남은 경기 (site/data/fixtures.js)"]
    rem = remaining_daegu_fixtures()
    for g in rem:
        o = g["away"] if g["home"] == MY_TEAM else g["home"]
        mark = " ← 상위 6팀" if o in top6 else ""
        L.append(f"- R{g['round']} {g['date']} {'홈' if g['home'] == MY_TEAM else '원정'} {o} {g.get('time', '')}{mark}")
    n_top_rem = sum((g["away"] if g["home"] == MY_TEAM else g["home"]) in top6 for g in rem)
    L.append(f"- 남은 경기 중 상위 6팀 상대: {n_top_rem}경기"
             + ("" if n_top_rem == 1 else " ⚠️ 1장 둘째 문장('이 한 경기') 고칠 것"))

    # 7. 원고 붙여넣기용 (원고의 장·문장 위치로 표시)
    worst = max(top_games, key=lambda g: g["ga"] - g["gf"])
    L += ["", "## 7. 원고 붙여넣기용 문장 (숫자만 바뀜. [숫자:갱신] 표시는 지우고 붙일 것)", ""]
    L.append(f"- 맨 위 기준일: > {y}년 {int(m)}월 {int(d)}일 기준 ({DATA_AS_OF_NOTE} 시점, 공식 순위표와 대조)")
    if second["team"] == MY_TEAM:
        L.append("- 1장 첫 문장: ⚠️ 대구가 2위 → 문장 틀이 안 맞음. 직접 수정")
    else:
        L.append(f"- 1장 첫 문장: {eun(short(OPPONENT))} {opp['rank']}위({opp['matches']}경기 {opp['points']}점), "
                 f"대구는 {me['rank']}위({me['matches']}경기 {me['points']}점)다. "
                 f"2위 {short(second['team'])}({second['points']}점)와 대구의 차이는 {second['points'] - me['points']}점이다.")
    names = "·".join(short(t) for t in top_names)
    L.append(f"- 3장 첫 문장: 기준일 순위표 상위 5팀({names})과의 {s_top['n']}경기에서 대구는 {wdl(s_top)}, "
             f"경기당 승점 {ieotda(format(s_top['ppg'], '.2f'))}. "
             f"나머지 팀과의 {s_rest['n']}경기는 {wdl(s_rest)}, 경기당 승점 {ida(format(s_rest['ppg'], '.2f'))}.")
    L.append(f"- 3장 둘째 문장: 득점과 실점으로 보면 상위 5팀 상대 경기당 {s_top['gf']/s_top['n']:.2f}득 {s_top['ga']/s_top['n']:.2f}실, "
             f"나머지 상대 {s_rest['gf']/s_rest['n']:.2f}득 {s_rest['ga']/s_rest['n']:.2f}실이다.")
    L += ["- 3장 표:", "", "| 날짜 | 라운드 | 장소 | 상대 | 결과 |", "|---|---|---|---|---|"]
    for g in top_games:
        L.append(f"| {slash_date(g['date'])} | {g['round']} | {'홈' if g['is_home'] else '원정'} | {short(g['opp'])} | {g['gf']}:{g['ga']} |")
    L.append("")
    L.append(f"- 4장 첫 문장: 대구는 올해 홈 {s_home['n']}경기에서 {wdl(s_home)}, 경기당 승점 {ida(format(s_home['ppg'], '.2f'))}. "
             f"상위 5팀과의 홈 경기는 {s_top_home['n']}경기 {ieotda(wdl(s_top_home))}.")
    L.append(f"- 5장 한계 둘째 줄: - 상위 5팀 상대 경기는 {s_top['n']}경기뿐이다. {kr_date(worst['date'])} {short(worst['opp'])} "
             f"{'홈' if worst['is_home'] else '원정'} {worst['gf']}:{worst['ga']} 한 경기가 {s_top['n']}경기 실점 "
             f"{s_top['ga']}골 중 {worst['ga']}골을 차지한다.")
    if before and after:
        L.append(f"- 5장 한계 셋째 줄: - {s_top['n']}경기 중 {len(before)}경기({slash_date(before[0]['date'])}~{slash_date(before[-1]['date'])})는 "
                 f"김병수 감독 시절, {len(after)}경기는 {kr_date(COACH_CHANGE)} 최성용 감독 선임 이후다. 감독 교체 효과는 따로 떼어 보지 않았다.")
    L.append(f"- 5장 한계 마지막 줄: - 스냅샷: {int(m)}월 {int(d)}일 기준 숫자이며, 이후 경기 결과는 반영하지 않았다.")
    L.append(f"- 맨 아래 기준일: 기준일: {y}년 {int(m)}월 {int(d)}일 ({DATA_AS_OF_NOTE})")
    return L


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

    L += extra_sections(table, games, top_names)

    card = draw_card(split, top_names, as_of_text)
    out_dir = OUTPUT_DIR / "preview"; out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"preview_{OPPONENT}.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"숫자: {md}\n카드: {card}")


if __name__ == "__main__":
    main()
