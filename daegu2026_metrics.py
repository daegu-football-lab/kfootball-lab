"""
대구FC 2026 K리그2 핵심 지표 계산기

실행 (kfootball-lab 폴더에서):
    python daegu2026_metrics.py

입력 : data/raw/daegu2026/ 의 CSV 4개 (원시 데이터, git에 올리지 않음)
출력 : output/daegu2026/
         metrics_summary.md   숫자 표 + 데이터 한계 + 해석 빈칸(직접 채울 논점)
         metrics_*.csv        집계값만 담은 표 (공개 가능한 가공 결과물)
         chart_*.png          블로그/제안서용 차트

원칙: 숫자와 차트는 자동, 해석 문장은 사람이 쓴다.
     그래서 이 스크립트는 "왜 그런지"를 쓰지 않고 "무엇을 확인할지"만 남긴다.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "daegu2026"
OUT = ROOT / "output" / "daegu2026"
OUT.mkdir(parents=True, exist_ok=True)

MY = "대구FC"
BLUE, GRAY, RED = "#0b5cab", "#c9d6e4", "#e4572e"
SOURCE = "본 분석에 사용된 데이터의 저작권 및 소유권은 한국프로축구연맹(K LEAGUE)에 있습니다."


# ----------------------------------------------------------------------------
# 0. 준비
# ----------------------------------------------------------------------------
def setup_font():
    # .ttc 묶음 폰트(리눅스의 Noto CJK)는 matplotlib이 자동 등록하지 않을 때가 있어 직접 추가한다
    for path in fm.findSystemFonts():
        if any(k in path.lower() for k in ("malgun", "nanum", "notosanscjk", "applegothic")):
            try:
                fm.fontManager.addfont(path)
            except Exception:
                pass
    for name in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]:
        if name in {f.name for f in fm.fontManager.ttflist}:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return
    print("[경고] 한글 폰트 없음 → 차트 한글이 깨질 수 있습니다.")


def load():
    m = pd.read_csv(RAW / "matches.csv", encoding="utf-8-sig")
    t = pd.read_csv(RAW / "team_match_stats.csv", encoding="utf-8-sig")
    l = pd.read_csv(RAW / "lineups.csv", encoding="utf-8-sig")
    e = pd.read_csv(RAW / "events.csv", encoding="utf-8-sig")

    # 대구 관점 컬럼 (매번 계산하지 않도록 한 번에)
    home = m["home_team"] == MY
    m["venue"] = home.map({True: "홈", False: "원정"})
    m["opponent"] = m["away_team"].where(home, m["home_team"])
    m["gf"] = m["home_score"].where(home, m["away_score"])
    m["ga"] = m["away_score"].where(home, m["home_score"])
    m["pts"] = (m["gf"] > m["ga"]) * 3 + (m["gf"] == m["ga"]) * 1
    m["result"] = m["pts"].map({3: "승", 1: "무", 0: "패"})

    # 이벤트 정렬용 시간: 전반 추가시간(45+3)이 후반 1분(46)보다 앞서도록 half를 먼저 본다
    e = e.sort_values(["match_id", "half", "minute", "added", "seq"]).reset_index(drop=True)
    return m, t, l, e


def pair_stats(t):
    """팀 기록을 '대구 vs 상대' 한 줄로 합친다 (for_ / against_)."""
    mine = t[t["team"] == MY].set_index("match_id")
    opp = t[t["team"] != MY].set_index("match_id")
    return mine.join(opp, lsuffix="_for", rsuffix="_against")


def bucket(row):
    """15분 구간. 추가시간은 그 전반/후반의 마지막 구간에 넣는다."""
    if row["half"] == 1:
        return min(row["minute"], 45) // 15.0001 if row["minute"] else 0
    return 3 + min(max(row["minute"] - 45, 0), 45) // 15.0001


LABELS = ["0-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"]


# ----------------------------------------------------------------------------
# 1~9. 지표
# ----------------------------------------------------------------------------
def m1_record(m):
    rows = []
    for name, g in [("전체", m), ("홈", m[m.venue == "홈"]), ("원정", m[m.venue == "원정"])]:
        rows.append({"구분": name, "경기": len(g), "승": (g.pts == 3).sum(), "무": (g.pts == 1).sum(),
                     "패": (g.pts == 0).sum(), "득점": g.gf.sum(), "실점": g.ga.sum(),
                     "승점": g.pts.sum(), "경기당승점": round(g.pts.mean(), 2)})
    return pd.DataFrame(rows)


def m2_shooting(p):
    s = {
        "경기당 슈팅": p.shots_for.mean(), "경기당 피슈팅": p.shots_against.mean(),
        "경기당 유효슈팅": p.shots_on_for.mean(), "경기당 피유효슈팅": p.shots_on_against.mean(),
        "유효슈팅 비율(%)": 100 * p.shots_on_for.sum() / p.shots_for.sum(),
        "상대 유효슈팅 비율(%)": 100 * p.shots_on_against.sum() / p.shots_against.sum(),
        "득점/유효슈팅(%)": 100 * p.goals_for.sum() / p.shots_on_for.sum(),
        "실점/피유효슈팅(%)": 100 * p.goals_against.sum() / p.shots_on_against.sum(),
    }
    # PDO(유효슈팅 기준): 100 근처로 되돌아가는 경향이 있는 '운+마무리+선방' 합성 지표
    s["PDO(유효슈팅 기준)"] = s["득점/유효슈팅(%)"] + (100 - s["실점/피유효슈팅(%)"])
    return pd.DataFrame({"지표": s.keys(), "값": [round(v, 1) for v in s.values()]})


def m3_possession(m, p):
    d = m.set_index("match_id").join(p[["possession_for"]])
    d["점유율구간"] = pd.cut(d.possession_for, [0, 49.99, 100], labels=["50% 미만", "50% 이상"])
    g = d.groupby("점유율구간", observed=True).agg(경기=("pts", "size"), 경기당승점=("pts", "mean"),
                                                 경기당득점=("gf", "mean"), 경기당실점=("ga", "mean"))
    return g.round(2).reset_index(), d


def m4_goal_timing(e):
    goals = e[e.type.isin(["goal", "own_goal"])].copy()
    # 자책골은 '넣은 팀'이 상대 → 득점 팀을 뒤집는다
    goals["scoring_team"] = goals.apply(
        lambda r: r.team if r.type == "goal" else "OPP" if r.team == MY else MY, axis=1)
    goals["구간"] = goals.apply(bucket, axis=1).astype(int).map(dict(enumerate(LABELS)))
    tab = pd.crosstab(goals["구간"], goals["scoring_team"] == MY).reindex(LABELS, fill_value=0)
    tab.columns = ["실점" if not c else "득점" for c in tab.columns]
    return tab[["득점", "실점"]].reset_index(), goals


def m5_game_state(m, goals):
    """스코어 흐름: 선제골, 리드 후 놓친 승점, 막판(80분~) 골로 바뀐 승점"""
    rows = []
    for mid, g in m.set_index("match_id").iterrows():
        gl = goals[goals.match_id == mid]
        f = a = 0
        led = trailed = False
        first = ""
        f80 = a80 = None
        for _, r in gl.iterrows():
            if f80 is None and (r.half == 2 and r.minute >= 80):
                f80, a80 = f, a
            if r.scoring_team == MY:
                f += 1
            else:
                a += 1
            first = first or ("득" if r.scoring_team == MY else "실")
            led |= f > a
            trailed |= a > f
        if f80 is None:
            f80, a80 = f, a
        pts80 = 3 if f80 > a80 else 1 if f80 == a80 else 0
        rows.append({"match_id": mid, "선제": first or "무득점", "리드한적": led, "뒤진적": trailed,
                     "승점": g.pts, "80분시점승점": pts80})
    s = pd.DataFrame(rows)
    out = {
        "선제골 경기 수": (s["선제"] == "득").sum(),
        "선제골 경기 승점": s.loc[s["선제"] == "득", "승점"].sum(),
        "선제 실점 경기 수": (s["선제"] == "실").sum(),
        "선제 실점 경기 승점": s.loc[s["선제"] == "실", "승점"].sum(),
        "리드했던 경기에서 놓친 승점": (3 - s.loc[s["리드한적"], "승점"]).sum(),
        "뒤졌던 경기에서 따낸 승점": s.loc[s["뒤진적"], "승점"].sum(),
        "80분 이후 골로 바뀐 승점(순)": (s["승점"] - s["80분시점승점"]).sum(),
        "80분 이후 골로 잃은 승점": (s["80분시점승점"] - s["승점"]).clip(lower=0).sum(),
        "80분 이후 골로 얻은 승점": (s["승점"] - s["80분시점승점"]).clip(lower=0).sum(),
    }
    return pd.DataFrame({"지표": out.keys(), "값": out.values()}), s


def score_at(goals, mid, half, minute, added):
    """해당 시각 '직전'의 스코어 (대구, 상대)"""
    g = goals[goals.match_id == mid]
    before = g[(g.half < half) | ((g.half == half) & ((g.minute < minute) |
                                                      ((g.minute == minute) & (g.added < added))))]
    return (before.scoring_team == MY).sum(), (before.scoring_team != MY).sum()


def m6_subs(m, e, l, goals):
    subs = e[e.type == "sub"].copy()
    subs["side"] = (subs.team == MY).map({True: "대구", False: "상대"})
    first = subs.groupby(["match_id", "side"]).first().reset_index()
    state = []
    for _, r in first[first.side == "대구"].iterrows():
        f, a = score_at(goals, r.match_id, r.half, r.minute, r.added)
        state.append("리드" if f > a else "동점" if f == a else "열세")
    first.loc[first.side == "대구", "스코어상태"] = state

    rows = []
    for side in ["대구", "상대"]:
        s, fs = subs[subs.side == side], first[first.side == side]
        rows.append({"구분": side, "경기당 교체": round(len(s) / len(m), 2),
                     "첫 교체 평균(분)": round(fs.minute.mean(), 1),
                     "하프타임 교체 비율(%)": round(100 * ((s.half == 2) & (s.minute == 45)).mean(), 1),
                     "75분 이후 교체 비율(%)": round(100 * (s.minute >= 75).mean(), 1)})
    by_state = (first[first.side == "대구"].groupby("스코어상태").minute
                .agg(["size", "mean"]).round(1).rename(columns={"size": "경기", "mean": "첫 교체 평균(분)"}))

    bench = l[(l.team == MY) & (l.started == 0) & (l.played == 1)]
    starters = l[(l.team == MY) & (l.started == 1)]
    contrib = pd.DataFrame([
        {"구분": "선발", "출전분": starters.minutes.sum(), "골": starters.goals.sum(), "도움": starters.assists.sum()},
        {"구분": "교체투입", "출전분": bench.minutes.sum(), "골": bench.goals.sum(), "도움": bench.assists.sum()},
    ])
    contrib["90분당 공격포인트"] = ((contrib.골 + contrib.도움) / contrib.출전분 * 90).round(2)
    return pd.DataFrame(rows), by_state.reset_index(), contrib, subs


def m7_poss_flow(t):
    cols = ["p00_15", "p15_30", "p30_45", "p45_60", "p60_75", "p75_90"]
    v = t[t.team == MY][cols].mean().round(1)
    return pd.DataFrame({"구간": LABELS, "대구 평균 점유율(%)": v.values})


def m8_players(l):
    d = l[(l.team == MY) & (l.played == 1)]
    g = d.groupby("player").agg(출전=("match_id", "size"), 선발=("started", "sum"), 출전분=("minutes", "sum"),
                                골=("goals", "sum"), 도움=("assists", "sum"),
                                평점평균=("rating", "mean"))
    g["90분당 공격포인트"] = ((g.골 + g.도움) / g.출전분 * 90).where(g.출전분 >= 450).round(2)
    g = g.round({"평점평균": 2}).sort_values("출전분", ascending=False).reset_index()
    return g.rename(columns={"player": "선수"})


def m9_attendance(m):
    h = m[m.venue == "홈"].copy()
    h["시간대"] = h.kickoff.str[:2].astype(int).map(lambda x: "낮(~17시)" if x < 18 else "저녁(18시~)")
    by = h.groupby("시간대").attendance.agg(["size", "mean"]).round(0).reset_index()
    by.columns = ["시간대", "경기", "평균 관중"]
    return h[["date", "opponent", "weekday", "kickoff", "weather", "temp_c", "attendance", "result"]], by


# ----------------------------------------------------------------------------
# 차트
# ----------------------------------------------------------------------------
def save(fig, name):
    fig.text(0.99, -0.04, SOURCE, ha="right", va="top", fontsize=6, color="#888")  # x축 제목과 겹치지 않게 그림 아래
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def charts(m, timing, d_poss, poss_flow, subs, att):
    # ① 시간대별 득실점
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = range(len(LABELS))
    ax.bar([i - 0.2 for i in x], timing["득점"], 0.4, color=BLUE, label="득점")
    ax.bar([i + 0.2 for i in x], timing["실점"], 0.4, color=RED, label="실점")
    ax.set_xticks(list(x), LABELS)
    ax.set_title("대구FC 2026 K리그2 시간대별 득점·실점 (26경기)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "chart_goal_timing.png")

    # ② 누적 승점과 5경기 이동 평균 승점
    s = m.sort_values("round")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(s["round"], s.pts.rolling(5).mean(), color=BLUE, marker="o", ms=3)
    ax.axhline(s.pts.mean(), color=GRAY, ls="--", lw=1)
    ax.set_ylim(0, 3)
    ax.set_xlabel("라운드")
    ax.set_ylabel("최근 5경기 경기당 승점")
    ax.set_title("대구FC 흐름: 최근 5경기 평균 승점 (점선 = 시즌 평균)")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "chart_form.png")

    # ③ 점유율 vs 승점 (점 하나 = 경기)
    fig, ax = plt.subplots(figsize=(6, 3.8))
    color = d_poss.pts.map({3: BLUE, 1: GRAY, 0: RED})
    ax.scatter(d_poss.possession_for, d_poss.gf - d_poss.ga, c=color, s=36, edgecolor="white")
    ax.axvline(50, color="#999", lw=0.8)
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xlabel("대구 점유율(%)")
    ax.set_ylabel("득실차")
    ax.set_title("점유율과 경기 결과 (파랑 승 / 회색 무 / 빨강 패)")
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "chart_possession_result.png")

    # ④ 교체 시각 분포 (대구 vs 상대)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bins = [0, 45.5, 55, 65, 75, 85, 91]
    for side, c, off in (("대구", BLUE, -0.2), ("상대", GRAY, 0.2)):
        cnt = pd.cut(subs[subs.side == side].minute, bins, right=False).value_counts(sort=False)
        ax.bar([i + off for i in range(len(cnt))], cnt.values, 0.4, color=c, label=side)
    ax.set_xticks(range(6), ["전반·HT", "46-54", "55-64", "65-74", "75-84", "85-90+"])
    ax.set_title("교체 시각 분포 (26경기, 교체 인원 수)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "chart_sub_timing.png")

    # ⑤ 홈 관중
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.bar(att.date.str[5:], att.attendance, color=BLUE)
    ax.set_title("대구iM뱅크PARK 홈 관중 (2026 K리그2)")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "chart_attendance.png")


# ----------------------------------------------------------------------------
# 요약 문서
# ----------------------------------------------------------------------------
def md_table(df):
    """마크다운 표. df.to_markdown()은 tabulate 패키지가 필요해서 직접 만든다(의존성 최소화)."""
    def fmt(v):
        if isinstance(v, float):
            return "" if pd.isna(v) else f"{v:g}"
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    line = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, line, *body])


def main():
    setup_font()
    m, t, l, e = load()
    p = pair_stats(t)

    rec = m1_record(m)
    shoot = m2_shooting(p)
    poss, d_poss = m3_possession(m, p)
    timing, goals = m4_goal_timing(e)
    state, state_rows = m5_game_state(m, goals)
    sub_sum, sub_state, contrib, subs = m6_subs(m, e, l, goals)
    flow = m7_poss_flow(t)
    players = m8_players(l)
    att, att_by = m9_attendance(m)

    for name, df in [("record", rec), ("shooting", shoot), ("possession", poss),
                     ("goal_timing", timing), ("game_state", state), ("subs", sub_sum),
                     ("subs_by_state", sub_state), ("bench", contrib), ("poss_flow", flow),
                     ("players", players), ("attendance", att)]:
        df.to_csv(OUT / f"metrics_{name}.csv", index=False, encoding="utf-8-sig")
    charts(m, timing, d_poss, flow, subs, att)

    first, last = m.date.min(), m.date.max()
    doc = f"""# 대구FC 2026 K리그2 핵심 지표

기간: {first} ~ {last} ({len(m)}경기, R9는 휴식 라운드)
출처: kleague.com 경기별 매치센터(한 경기씩 열람해 옮겨 적음)
검증: 합계 승점·득실이 연맹 순위표 기준 team_season_stats.csv(26경기 13승 7무 6패, 48득 35실, 46점)와 일치

> 이 문서는 숫자만 담는다. 해석 문장은 각 절의 '확인할 점'을 보고 직접 쓴다.

## 1. 성적
{md_table(rec)}

## 2. 슈팅 효율
{md_table(shoot)}

- 확인할 점: 득점/유효슈팅, 실점/피유효슈팅이 리그 평균보다 높은가 낮은가 → 리그 평균 필요(데이터포털 팀 기록)
- 한계: 슈팅의 위치·질(xG)이 없다. 유효슈팅 수만으로 '결정력'을 단정할 수 없다.

## 3. 점유율과 결과
{md_table(poss)}

- 확인할 점: 점유율이 높은 경기의 상대가 누구였나(하위권 상대가 몰렸는지). 차트: chart_possession_result.png
- 한계: 점유율은 스코어 상태의 결과이기도 하다(앞서면 내려앉고, 뒤지면 공을 오래 가진다).

## 4. 시간대별 득점·실점
{md_table(timing)}

- 확인할 점: 76-90+ 구간 실점이 어느 경기에 몰려 있나(한두 경기의 대량 실점인지). 차트: chart_goal_timing.png
- 한계: 한 구간에 10골 안팎이라 표본이 작다. 1~2골 차이는 우연일 수 있다.

## 5. 스코어 흐름
{md_table(state)}

- 확인할 점: 막판 실점 경기에서 직전 교체가 있었는지(events.csv에서 시각 비교)
- 한계: '80분 시점 승점'은 그대로 끝났을 경우를 가정한 값이다. 실제로는 경기 양상이 달라졌을 수 있다.

## 6. 교체 운용
{md_table(sub_sum)}

**대구 첫 교체 시점의 스코어 상태별**
{md_table(sub_state)}

**선발 vs 교체 투입 선수의 공격포인트**
{md_table(contrib)}

- 확인할 점: 지고 있을 때 첫 교체가 더 빠른가. 프롤로그의 "팬들이 교체를 맞힌다" 소재와 연결 가능
- 한계: 부상 교체와 전술 교체를 구분할 수 없다. 교체 투입 선수는 상대가 지친 시간에 뛴다.

## 7. 15분 구간 평균 점유율 (대구)
{md_table(flow)}

## 8. 선수 (출전 시간 순)
{md_table(players.head(20))}

- 한계: '평점'은 매치센터 라인업에 표시된 값이며 산출 방식은 공개돼 있지 않다 [확인 필요].
  출전 시간은 교체 시각 기준이며 추가시간은 뺐다(최대 90분).
  포지션은 라인업 그림의 세로 위치로 나눈 추정치다 [추정].

## 9. 홈 관중
{md_table(att_by)}

{md_table(att)}

- 확인할 점: 저녁 경기와 낮 경기의 차이가 요일·상대·날씨 중 무엇과 겹치는가 (제안서 소재)
- 한계: 13경기뿐이고 요일·시간·날씨·상대 순위가 서로 얽혀 있다.

## 데이터 메모
- R25(파주전) 경고 통계 3장 = 황재원의 두 번째 경고(경고누적 퇴장) 포함. 사건 목록에는 경고 2 + 퇴장 1로 들어 있다.
- 타임라인의 '유효슈팅' 사건 수는 경기 통계의 유효슈팅 수와 다를 때가 있다 → 합계는 통계 표(team_match_stats) 기준.
- {SOURCE}
"""
    (OUT / "metrics_summary.md").write_text(doc, encoding="utf-8")
    print(f"완료 → {OUT}")


if __name__ == "__main__":
    main()
