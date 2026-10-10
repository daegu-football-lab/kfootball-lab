"""3편 [분석 #3] 카드 2장: 경기 순서별 홈 관중(IMG-01) + 직전 결과별 관중 변화(IMG-02).

숫자는 data/raw/daegu2026/matches.csv에서 계산합니다(원시 파일은 공개 안 함, 그림만 공개).
3편 본문 표(posts/attendance_draft_v3.md)와 값이 다르면 멈춥니다 → 글과 그림이 다른 말을 하지 않게.
실행: python card_03_attendance.py   (결과: output/charts/card_03_attendance_*.png)
"""
import csv
import statistics as st
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def rnd(x):
    """보통 반올림(.5는 0에서 먼 쪽으로). 파이썬 round()는 -686.5 → -686(짝수 쪽)이라 글 표기와 어긋남."""
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

from pathlib import Path

from src import card_style as cs

ROOT = Path(__file__).parent
AS_OF = "기준일: 2026년 9월 30일 · 관중: K리그 공식 홈페이지 관중 현황"
SERIES = ("대구FC 홈경기 읽기", "①", "관중 × 성적")

# 3편 본문 표 값(검증용): 기준 → 결과 → (경기 수, 평균)
EXPECTED = {"A": {"승": (5, 173), "무": (4, -860), "패": (3, -99)},
            "B": {"승": (7, 255), "무": (2, -687), "패": (3, -1096)}}


def load():
    rows = sorted(csv.DictReader(open(ROOT / "data/raw/daegu2026/matches.csv", encoding="utf-8-sig")),
                  key=lambda r: r["date"])
    is_home = lambda r: r["home_team"].startswith("대구")

    def result(r):
        gf, ga = (int(r["home_score"]), int(r["away_score"])) if is_home(r) else (int(r["away_score"]), int(r["home_score"]))
        return "승" if gf > ga else "무" if gf == ga else "패"

    home_idx = [i for i, r in enumerate(rows) if is_home(r)]
    games = []
    for k, i in enumerate(home_idx):
        r = rows[i]
        g = dict(date=r["date"], att=int(r["attendance"]), weather=r["weather"], gap=None, A=None, B=None, delta=None)
        if k:
            prev_home = rows[home_idx[k - 1]]
            g["gap"] = (date.fromisoformat(r["date"]) - date.fromisoformat(prev_home["date"])).days
            g["A"], g["B"] = result(rows[i - 1]), result(prev_home)   # A: 직전 경기(원정 포함), B: 직전 홈경기
            g["delta"] = g["att"] - int(prev_home["attendance"])
        games.append(g)
    return games


def check(games):
    for key, exp in EXPECTED.items():
        for res, (n, mean) in exp.items():
            v = [g["delta"] for g in games if g[key] == res]
            assert (len(v), rnd(st.mean(v))) == (n, mean), f"본문 표와 다름: {key} {res} {len(v)} {rnd(st.mean(v))}"


def label(d):
    return f"{int(d[5:7])}/{int(d[8:])}"


def card_trend(games):
    y = [g["att"] for g in games]
    mean = st.mean(y)
    fig = cs.new_card(*SERIES, f"대구 홈 관중, 13경기 {min(y):,}~{max(y):,}명",
                      f"회색 숫자 = 며칠 만의 홈경기 · 점선 = 13경기 평균 {rnd(mean):,}명")
    ax = fig.add_axes([0.08, 0.20, 0.86, 0.48])
    x = range(len(games))
    ax.plot(x, y, color=cs.MUTED, lw=2, zorder=1)
    ax.scatter(x, y, s=140, color=cs.FOCUS, zorder=2)
    ax.axhline(mean, color=cs.MUTED, lw=1.5, ls=(0, (5, 4)), zorder=0)
    for i, g in enumerate(games):
        ax.text(i, g["att"] + 330, f"{g['att']:,}", ha="center", fontsize=15, color=cs.TEXT_1,
                bbox=dict(facecolor=cs.SURFACE, edgecolor="none", pad=1), zorder=3)
        if g["gap"]:
            ax.text(i, g["att"] + 760, f"{g['gap']}일", ha="center", fontsize=14, color=cs.TEXT_3,
                    bbox=dict(facecolor=cs.SURFACE, edgecolor="none", pad=1), zorder=3)
    # 특수 경기 표시: 개막전, 비 온 경기
    ax.text(0, games[0]["att"] - 650, "개막전", ha="center", fontsize=16, color=cs.FOCUS, weight="bold")
    for i, g in enumerate(games):
        if g["weather"] == "비":
            ax.text(i, g["att"] - 650, "비", ha="center", fontsize=16, color=cs.FOCUS, weight="bold")
    ax.set_xticks(list(x), [label(g["date"]) for g in games], fontsize=15, color=cs.TEXT_2)
    ax.set_ylim(6000, 13500)
    ax.set_yticks([6000, 8000, 10000, 12000], ["6,000", "8,000", "10,000", "12,000"], fontsize=15, color=cs.TEXT_3)
    ax.set_facecolor(cs.SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(cs.TRACK)
    ax.tick_params(length=0)
    ax.grid(axis="y", color=cs.TRACK, lw=1)
    ax.set_axisbelow(True)
    cs.add_footer(fig, AS_OF)
    return fig


def card_split(games):
    fig = cs.new_card(*SERIES, "직전 결과별, 다음 홈경기 관중 변화",
                      "점 = 경기 1개 · 가로선 = 평균 · 0보다 위면 직전 홈경기보다 관중이 늘었다는 뜻")
    panels = [("A", "기준 A · 바로 앞 경기(원정 포함)", 0.08), ("B", "기준 B · 바로 앞 홈경기", 0.54)]
    for key, title, left in panels:
        ax = fig.add_axes([left, 0.20, 0.40, 0.44])
        fig.text(left, 0.675, title, fontsize=20, color=cs.TEXT_1, weight="bold")
        for xi, res in enumerate(("승", "무", "패")):
            v = sorted(g["delta"] for g in games if g[key] == res)
            # 같은 값이 겹치지 않게 가로로 살짝 벌림(무작위 대신 고정 간격 → 다시 그려도 같은 그림)
            offs = [(j - (len(v) - 1) / 2) * 0.09 for j in range(len(v))]
            color = cs.FOCUS if res == "승" else cs.MUTED
            ax.scatter([xi + o for o in offs], v, s=150, color=color, zorder=3, edgecolor="white", lw=1.5)
            m = st.mean(v)
            ax.plot([xi - 0.28, xi + 0.28], [m, m], color=cs.TEXT_1, lw=3, zorder=4)
            ax.text(xi + 0.32, m, f"{rnd(m):+,}", va="center", fontsize=15, color=cs.TEXT_1)
        ax.axhline(0, color=cs.TEXT_3, lw=1.2, zorder=1)
        counts = [sum(g[key] == r for g in games) for r in ("승", "무", "패")]
        ax.set_xticks([0, 1, 2], [f"직전 {r}\n({n}경기)" for r, n in zip(("승", "무", "패"), counts)],
                      fontsize=16, color=cs.TEXT_2)
        ax.set_xlim(-0.6, 2.75)
        ax.set_ylim(-2800, 2800)
        ax.set_yticks([-2000, -1000, 0, 1000, 2000], ["-2,000", "-1,000", "0", "+1,000", "+2,000"],
                      fontsize=14, color=cs.TEXT_3)
        ax.set_facecolor(cs.SURFACE)
        for s in ("top", "right", "left", "bottom"):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
        ax.grid(axis="y", color=cs.TRACK, lw=1)
        ax.set_axisbelow(True)
    cs.add_footer(fig, AS_OF + " · 개막전은 직전 홈경기가 없어 제외(12경기)")
    return fig


if __name__ == "__main__":
    games = load()
    check(games)
    out = ROOT / "output" / "charts"
    out.mkdir(parents=True, exist_ok=True)
    card_trend(games).savefig(out / "card_03_attendance_trend.png", facecolor=cs.SURFACE)
    card_split(games).savefig(out / "card_03_attendance_split.png", facecolor=cs.SURFACE)
    print("ok", [p.name for p in out.glob("card_03_*")])
