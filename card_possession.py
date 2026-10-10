"""[분석 #3] 점유율이 높으면 대구는 이길까? — 카드 2장 + 사이트 데이터 + 본문 숫자.

숫자는 손으로 적지 않고 data/raw/daegu2026/ 원시 기록에서 계산합니다.
실행: python card_possession.py
  결과 ① output/charts/card_poss_*.png (블로그 그림)
       ② site/data/possession.js     (사이트 '팀 비교' 탭. 집계값만, 경기별 원시 기록은 넣지 않음)
       ③ 화면 출력                    (본문 빈칸용 숫자)

검증: 경기 수가 EXPECTED와 같으면 본문에 적은 값과 대조해서 다르면 멈춥니다.
      새 경기를 추가해 경기 수가 늘면 대조를 건너뛰고 "본문 숫자 갱신 필요"를 알립니다.

용어
  점유율 구간: 경기 전체 점유율로 나눔. 50% 미만 / 50~59% / 60% 이상
  스코어 상황: 15분 구간(0-15 … 75-90)마다, 그 구간이 '시작될 때'의 스코어로 앞섬/동점/뒤짐을 나눔
               (구간 중간에 골이 나면 상황이 바뀌지만 구간 점유율은 하나뿐이라 근사값)
  감독: 김병수 감독 경질 2026-04-20 [확인: 언론 보도, 프로젝트 문서 17번] → 그 전 경기 = 김병수, 이후 = 최성용
"""
import json
from pathlib import Path

import pandas as pd

from src import card_style as cs

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw" / "daegu2026"
OUT = ROOT / "output" / "charts"
SITE_JS = ROOT / "site" / "data" / "possession.js"
TEAM = "대구FC"

COACH_CHANGE = "2026-04-20"          # 이 날짜 전 경기는 김병수, 이후는 최성용
COACHES = ["김병수", "최성용"]
SMALL_N = 5                          # 이보다 적은 경기 수는 '표본 적음' 표시

BINS = [0, 49.99, 59.99, 100]
LABELS = ["50% 미만", "50~59%", "60% 이상"]
STATES = ["앞섬", "동점", "뒤짐"]
STATE_TEXT = {"앞섬": "앞설 때", "동점": "동점일 때", "뒤짐": "뒤질 때"}
IV_COLS = ["p00_15", "p15_30", "p30_45", "p45_60", "p60_75", "p75_90"]
IV_START = [0, 15, 30, 45, 60, 75]

# 본문에 적은 값 (검증용). 구간: (경기, 승, 무, 패, 경기당 승점) / 상황: (구간 수, 평균 점유율)
EXPECTED = {
    "games": 26,
    "구간": {"50% 미만": (9, 3, 4, 2, 1.44), "50~59%": (12, 9, 2, 1, 2.42), "60% 이상": (5, 1, 1, 3, 0.80)},
    "상황": {"앞섬": (36, 47.9), "동점": (89, 53.7), "뒤짐": (31, 58.4)},
    "감독": {"김병수": (8, 3, 2, 3, 1.38, 56.0), "최성용": (18, 10, 5, 3, 1.94, 51.3)},
    "감독상황": {"김병수": {"앞섬": (14, 50.8), "동점": (18, 54.9), "뒤짐": (16, 60.9)},
               "최성용": {"앞섬": (22, 46.1), "동점": (71, 53.4), "뒤짐": (15, 55.8)}},
}


# ---------------------------------------------------------------- 데이터
def load_goals():
    """골 사건(자책골 포함). team = 득점이 인정된 팀. abs = 경기 시각(추가시간은 소수점으로 뒤에 붙임)."""
    e = pd.read_csv(RAW / "events.csv")
    g = e[e.type.isin(["goal", "own_goal"])].copy()
    g["abs"] = g.minute.clip(upper=g.half.map({1: 45, 2: 90})) + g.added * 0.01
    return g


def coach_of(date):
    return "김병수" if date < COACH_CHANGE else "최성용"


def load_matches():
    """대구 경기: 점유율, 득실, 결과, 선제골 팀, 상대 현재 순위, 감독."""
    m = pd.read_csv(RAW / "matches.csv")
    t = pd.read_csv(RAW / "team_match_stats.csv")
    d = t[t.team == TEAM].merge(m, on="match_id")
    home = d.home_team == TEAM
    d["opp"] = d.away_team.where(home, d.home_team)
    d["gf"] = d.home_score.where(home, d.away_score)
    d["ga"] = d.away_score.where(home, d.home_score)
    d["res"] = ["승" if f > a else "무" if f == a else "패" for f, a in zip(d.gf, d.ga)]
    d["pts"] = d.res.map({"승": 3, "무": 1, "패": 0})
    d["bin"] = pd.cut(d.possession, BINS, labels=LABELS)
    d["coach"] = d.date.map(coach_of)

    first = load_goals().sort_values(["match_id", "abs"]).groupby("match_id").team.first()
    d["first"] = d.match_id.map(lambda i: "없음" if i not in first.index else ("대구" if first[i] == TEAM else "상대"))

    js = (ROOT / "site" / "data" / "standings.js").read_text(encoding="utf-8")
    rank = {x["team"]: x["총점순위"] for x in json.loads(js[js.index("{"): js.rindex("}") + 1])["teams"]}
    d["opp_rank"] = d.opp.map(rank)
    return d


def score_state_intervals(d):
    """15분 구간마다 (구간 시작 때 스코어 상황, 대구 점유율, 감독)."""
    goals = load_goals()
    rows = []
    for _, r in d.iterrows():
        gm = goals[goals.match_id == r.match_id]
        for col, start in zip(IV_COLS, IV_START):
            before = gm[gm["abs"] < start]
            diff = (before.team == TEAM).sum() - (before.team != TEAM).sum()
            state = "앞섬" if diff > 0 else "뒤짐" if diff < 0 else "동점"
            rows.append({"match_id": r.match_id, "coach": r.coach, "state": state, "poss": float(r[col])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 집계
def bin_table(d):
    out = {}
    for b in LABELS:
        x = d[d.bin == b]
        out[b] = (len(x), int((x.res == "승").sum()), int((x.res == "무").sum()), int((x.res == "패").sum()),
                  round(float(x.pts.mean()), 2) if len(x) else None)
    return out


def state_table(iv):
    return {s: (len(x), round(float(x.poss.mean()), 1)) for s, x in iv.groupby("state")}


def coach_table(d):
    out = {}
    for c in COACHES:
        x = d[d.coach == c]
        out[c] = (len(x), int((x.res == "승").sum()), int((x.res == "무").sum()), int((x.res == "패").sum()),
                  round(float(x.pts.mean()), 2), round(float(x.possession.mean()), 1))
    return out


def check(d, iv):
    """경기 수가 그대로면 본문 값과 대조. 다르면 갱신 필요만 알림."""
    if len(d) != EXPECTED["games"]:
        print(f"⚠ 경기 수 {EXPECTED['games']} → {len(d)}: 새 경기 반영됨. 본문 숫자와 EXPECTED 갱신 필요")
        return
    assert bin_table(d) == EXPECTED["구간"], bin_table(d)
    assert state_table(iv) == EXPECTED["상황"], state_table(iv)
    assert coach_table(d) == EXPECTED["감독"], coach_table(d)
    for c in COACHES:
        assert state_table(iv[iv.coach == c]) == EXPECTED["감독상황"][c], (c, state_table(iv[iv.coach == c]))
    print("✓ 본문 숫자와 일치")


def as_of(d):
    return f"기준: 2026 K리그2 {int(d['round'].max())}라운드 종료 (대구 {len(d)}경기) · 기록: K리그 공식 홈페이지 매치센터"


# ---------------------------------------------------------------- 카드
def _clean_axes(ax):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(left=False)
    ax.set_xticks([])


def card_bins(d):
    """IMG-01: 점유율 구간별 경기당 승점 (시즌 전체)."""
    by_bin = bin_table(d)
    avg = d.pts.mean()
    fig = cs.new_card("대구FC 시즌 기록", "①", "점유율", "점유율 구간별 경기당 승점",
                      f"경기 전체 점유율로 {len(d)}경기를 셋으로 나눴다. 막대 = 경기당 평균 승점")
    ax = fig.add_axes([0.20, 0.20, 0.52, 0.46], facecolor=cs.SURFACE)
    ys = [2, 1, 0]
    vals = [by_bin[b][4] for b in LABELS]
    ax.barh(ys, vals, color=[cs.MUTED, cs.MUTED, cs.FOCUS], height=0.55, zorder=2)  # 막대가 기준 점선을 덮도록
    for y, v, (n, w, dr, l, _) in zip(ys, vals, by_bin.values()):
        ax.text(v - 0.045, y, f"{v:.2f}", va="center", ha="right", fontsize=26, weight="bold", color="white")
        ax.text(1.04, y, f"{n}경기 · {w}승 {dr}무 {l}패", va="center", fontsize=21, color=cs.TEXT_2,
                transform=ax.get_yaxis_transform())
    ax.axvline(avg, color=cs.TEXT_3, linestyle=(0, (4, 4)), linewidth=1.5, zorder=1)
    ax.text(avg, 2.55, f"시즌 평균 {avg:.2f}", ha="center", fontsize=17, color=cs.TEXT_3)
    ax.set_yticks(ys, LABELS, fontsize=24, color=cs.TEXT_1)
    ax.set_xlim(0, 3.0)
    _clean_axes(ax)
    cs.add_footer(fig, as_of(d))
    fig.savefig(OUT / "card_poss_01_구간별승점.png", facecolor=cs.SURFACE)


def card_states(d, iv):
    """IMG-02: 스코어 상황별 점유율, 감독별 두 막대 (현 감독 최성용만 파랑)."""
    fig = cs.new_card("대구FC 시즌 기록", "②", "점유율", "스코어 상황별 대구 점유율, 감독별",
                      "15분 구간마다, 구간이 시작될 때의 스코어로 나눈 평균 점유율")
    ax = fig.add_axes([0.20, 0.17, 0.52, 0.52], facecolor=cs.SURFACE)
    h = 0.36
    for k, (coach, color) in enumerate([("김병수", cs.MUTED), ("최성용", cs.FOCUS)]):
        tab = state_table(iv[iv.coach == coach])
        for j, s in enumerate(STATES):
            y = (2 - j) + (h / 2 if k == 0 else -h / 2)
            n, v = tab[s]
            ax.barh(y, v, height=h * 0.92, color=color, zorder=2)
            ax.text(v - 0.8, y, f"{v:.1f}%", va="center", ha="right", fontsize=20, weight="bold", color="white")
            ax.text(1.03, y, f"{coach} {n}구간", va="center", fontsize=17,
                    color=cs.FOCUS if k else cs.TEXT_2, transform=ax.get_yaxis_transform())
    ax.axvline(50, color=cs.TEXT_3, linestyle=(0, (4, 4)), linewidth=1.5, zorder=1)
    ax.text(50, 2.62, "50%", ha="center", fontsize=17, color=cs.TEXT_3)
    ax.set_yticks([2, 1, 0], [STATE_TEXT[s] for s in STATES], fontsize=24, color=cs.TEXT_1)
    ax.set_xlim(0, 75)
    _clean_axes(ax)
    n_k, n_c = (d.coach == "김병수").sum(), (d.coach == "최성용").sum()
    fig.text(0.94, 0.755, f"회색 김병수 {n_k}경기 · 파랑 최성용 {n_c}경기", fontsize=19, color=cs.TEXT_2, ha="right")
    cs.add_footer(fig, as_of(d))
    fig.savefig(OUT / "card_poss_02_스코어상황.png", facecolor=cs.SURFACE)


# ---------------------------------------------------------------- 사이트 데이터
def export_site(d, iv):
    """집계값만 내보냅니다(경기별 점유율·스코어 같은 원시 기록은 넣지 않음)."""
    def group(x, y):
        bins = [{"label": b, "n": n, "w": w, "d": dr, "l": l, "ppg": p}
                for b, (n, w, dr, l, p) in bin_table(x).items()]
        tab = state_table(y)
        states = [{"label": STATE_TEXT[s], "intervals": tab.get(s, (0, None))[0], "poss": tab.get(s, (0, None))[1]}
                  for s in STATES]
        return {"games": len(x), "ppg": round(float(x.pts.mean()), 2),
                "poss": round(float(x.possession.mean()), 1), "bins": bins, "states": states}

    data = {
        "meta": {"team": TEAM, "round": int(d["round"].max()), "games": len(d), "small_n": SMALL_N,
                 "coach_change": COACH_CHANGE,
                 "source": "K리그 공식 홈페이지 매치센터 (경기별 기록을 직접 옮겨 적어 집계)"},
        "groups": {"전체": group(d, iv), **{c: group(d[d.coach == c], iv[iv.coach == c]) for c in COACHES}},
    }
    SITE_JS.write_text("// 대구FC 점유율 집계 (python card_possession.py 로 다시 만듭니다. 손으로 고치지 마세요)\n"
                       f"window.KFL_POSSESSION = {json.dumps(data, ensure_ascii=False)};\n", encoding="utf-8")


# ---------------------------------------------------------------- 본문 숫자
def print_numbers(d, iv):
    hi = d[d.bin == "60% 이상"].sort_values("possession", ascending=False)
    print("[60% 이상 경기]")
    print(hi[["round", "date", "coach", "opp", "venue", "possession", "gf", "ga", "res", "first", "opp_rank"]]
          .to_string(index=False))
    print("\n[구간별 · 시즌] (경기, 승, 무, 패, 경기당 승점) / 득점·실점·상대 평균 순위")
    for b in LABELS:
        x = d[d.bin == b]
        print(" ", b, bin_table(d)[b], round(x.gf.mean(), 2), round(x.ga.mean(), 2), round(x.opp_rank.mean(), 1))
    print("\n[감독별] (경기, 승, 무, 패, 경기당 승점, 평균 점유율) / 득점·실점·상대 평균 순위·60% 이상 경기")
    for c in COACHES:
        x = d[d.coach == c]
        print(" ", c, coach_table(d)[c], round(x.gf.mean(), 2), round(x.ga.mean(), 2),
              round(x.opp_rank.mean(), 1), int((x.bin == "60% 이상").sum()))
        print("    구간별", bin_table(x))
        print("    상황별", state_table(iv[iv.coach == c]))
    print("\n[선제골별] 경기 수, 평균 점유율, 경기당 승점")
    print(d.groupby("first").agg(n=("pts", "size"), poss=("possession", "mean"), ppg=("pts", "mean")).round(2))
    print("\n[스코어 상황별 · 시즌]", state_table(iv))
    print("시즌 평균 점유율", round(d.possession.mean(), 1), "/ 경기당 승점", round(d.pts.mean(), 2))


def build():
    d = load_matches()
    iv = score_state_intervals(d)
    check(d, iv)
    OUT.mkdir(parents=True, exist_ok=True)
    card_bins(d)
    card_states(d, iv)
    export_site(d, iv)
    print_numbers(d, iv)


if __name__ == "__main__":
    build()
