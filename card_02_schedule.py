"""2편 [분석 #2] 카드 2장: 잔여 일정 요약(IMG-01) + 팀 x 라운드 일정표(IMG-02).

숫자는 손으로 적지 않고 site/data/fixtures.js + standings.js에서 계산합니다.
계산 결과가 2편 표(9/29 재계산값)와 다르면 멈춥니다 → 글과 그림이 다른 말을 하지 않게.
실행: python card_02_schedule.py   (결과: output/charts/card_02_*.png)
"""
import json
import re
from pathlib import Path

from src import card_style as cs

ROOT = Path(__file__).parent
AS_OF = "기준일: 2026년 9월 30일 (27라운드 종료) · 일정: K리그 공식 홈페이지"
FOCUS_TEAM = "대구FC"
ROUNDS = range(28, 35)

# 2편 본문 표 값 (검증용). 팀: (남은 경기, 상위6 맞대결, 홈, 상대 평균 순위)
EXPECTED = {"수원삼성": (7, 2, 4, 10.3), "수원FC": (7, 1, 5, 9.3), "서울이랜드": (6, 0, 3, 11.7),
            "대구FC": (6, 1, 3, 11.5), "화성FC": (6, 2, 0, 8.0), "부산아이파크": (6, 0, 3, 11.7)}


def load_js(name):
    """window.X = {...}; 형태의 JS 파일에서 JSON 부분만 읽습니다."""
    text = (ROOT / "site" / "data" / name).read_text(encoding="utf-8")
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def short(team):
    """칸이 좁아서 긴 이름만 줄입니다. 수원FC는 수원삼성과 구분하려고 그대로 둡니다."""
    if team == "수원FC":
        return team
    return re.sub(r"(FC|그리너스|드래곤즈|프런티어|아이파크|시티)$", "", team).replace("서울이랜드", "서울E")


def build():
    rank = {t["team"]: t["총점순위"] for t in load_js("standings.js")["teams"]}
    fixtures = load_js("fixtures.js")["fixtures"]
    top6 = sorted([t for t in rank if rank[t] <= 6], key=rank.get)

    rows = {}
    for team in top6:
        games = {}
        for f in fixtures:
            if team in (f["home"], f["away"]):
                opp = f["away"] if f["home"] == team else f["home"]
                games[f["round"]] = (opp, f["home"] == team)
        n = len(games)
        vs_top = sum(rank[o] <= 6 for o, _ in games.values())
        home = sum(h for _, h in games.values())
        avg = round(sum(rank[o] for o, _ in games.values()) / n, 1)
        assert (n, vs_top, home, avg) == EXPECTED[team], f"{team}: {(n, vs_top, home, avg)} != {EXPECTED[team]}"
        rows[team] = dict(games=games, n=n, vs_top=vs_top, home=home, avg=avg)
    return rank, top6, rows


def card_summary(top6, rows):
    """IMG-01: 상대 평균 순위 점 그래프 (순위라서 막대 대신 점)."""
    fig = cs.new_card("K리그2 승격 경쟁", "②", "잔여 일정",
                      "상위 6팀, 남은 상대의 평균 순위",
                      "점이 왼쪽일수록 순위가 높은 상대를 많이 만난다 (숫자가 작을수록 상위권)")
    ax = fig.add_axes([0.21, 0.17, 0.49, 0.53], facecolor=cs.SURFACE)
    for i, team in enumerate(top6):
        r = rows[team]
        color = cs.FOCUS if team == FOCUS_TEAM else cs.MUTED
        ax.plot([1, 17], [i, i], color=cs.TRACK, lw=2, zorder=1)
        ax.scatter(r["avg"], i, s=420, color=color, zorder=3)
        ax.text(r["avg"], i - 0.38, f"{r['avg']:.1f}", ha="center", fontsize=20,
                color=cs.TEXT_1 if team == FOCUS_TEAM else cs.TEXT_2, weight="bold")
        fig.text(0.20, 0.17 + 0.53 * (len(top6) - 0.5 - i) / len(top6), f"{rank_label(i)} {team}",
                 ha="right", va="center", fontsize=23,
                 color=cs.FOCUS if team == FOCUS_TEAM else cs.TEXT_1,
                 weight="bold" if team == FOCUS_TEAM else "normal")
        fig.text(0.735, 0.17 + 0.53 * (len(top6) - 0.5 - i) / len(top6),
                 f"{r['n']}경기 · 홈 {r['home']} · 맞대결 {r['vs_top']}",
                 va="center", fontsize=19, color=cs.TEXT_2)
    ax.set_xlim(0.5, 17.5)
    ax.set_ylim(len(top6) - 0.5, -0.7)
    ax.set_xticks([1, 6, 12, 17])
    ax.tick_params(labelsize=18, colors=cs.TEXT_3, length=0)
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    fig.text(0.21, 0.105, "◀ 상위권 상대", fontsize=18, color=cs.TEXT_3)
    fig.text(0.70, 0.105, "하위권 상대 ▶", fontsize=18, color=cs.TEXT_3, ha="right")
    fig.text(0.735, 0.715, "남은 경기 · 홈 경기 · 상위 6팀 맞대결", fontsize=16, color=cs.TEXT_3)
    cs.add_footer(fig, AS_OF + " · 상대 순위는 기준일 순위")
    return fig


def rank_label(i):
    return f"{i + 1}위"


def card_grid(rank, top6, rows):
    """IMG-02: 팀 x 라운드 일정표. 상위 6팀 상대 칸만 색칠."""
    fig = cs.new_card("K리그2 승격 경쟁", "②", "잔여 일정",
                      "라운드별 남은 상대 (28~34라운드)",
                      "파란 칸 = 상위 6팀과의 맞대결 · 칸 아래 홈/원정 · 휴식 = 경기 없는 라운드")
    x0, y0, w, h = 0.20, 0.14, 0.74, 0.58
    cw, ch = w / len(ROUNDS), h / (len(top6) + 1)
    for j, rnd in enumerate(ROUNDS):
        fig.text(x0 + cw * (j + 0.5), y0 + h - ch * 0.5, f"{rnd}R", ha="center", va="center",
                 fontsize=20, color=cs.TEXT_2, weight="bold")
    for i, team in enumerate(top6):
        yc = y0 + h - ch * (i + 1.5)
        fig.text(x0 - 0.01, yc, f"{i + 1}위 {team}", ha="right", va="center", fontsize=22,
                 color=cs.FOCUS if team == FOCUS_TEAM else cs.TEXT_1,
                 weight="bold" if team == FOCUS_TEAM else "normal")
        for j, rnd in enumerate(ROUNDS):
            game = rows[team]["games"].get(rnd)
            if game is None:
                fig.text(x0 + cw * (j + 0.5), yc, "휴식", ha="center", va="center", fontsize=18, color=cs.TEXT_3)
                continue
            opp, is_home = game
            is_top = rank[opp] <= 6
            fig.patches.append(cs.plt.Rectangle((x0 + cw * j + 0.003, yc - ch / 2 + 0.006), cw - 0.006, ch - 0.012,
                                                transform=fig.transFigure, facecolor=cs.FOCUS if is_top else cs.TRACK,
                                                edgecolor="none"))
            fg = "white" if is_top else cs.TEXT_1
            fig.text(x0 + cw * (j + 0.5), yc + 0.014, short(opp), ha="center", va="center", fontsize=20,
                     color=fg, weight="bold" if is_top else "normal")
            fig.text(x0 + cw * (j + 0.5), yc - 0.026, "홈" if is_home else "원정", ha="center", va="center",
                     fontsize=15, color="white" if is_top else cs.TEXT_3)
    cs.add_footer(fig, AS_OF + " · 상위 6팀 = 기준일 1~6위")
    return fig


if __name__ == "__main__":
    rank, top6, rows = build()
    out = ROOT / "output" / "charts"
    out.mkdir(parents=True, exist_ok=True)
    card_summary(top6, rows).savefig(out / "card_02_summary.png", facecolor=cs.SURFACE)
    card_grid(rank, top6, rows).savefig(out / "card_02_grid.png", facecolor=cs.SURFACE)
    for t in top6:
        r = rows[t]
        print(t, r["n"], r["vs_top"], r["home"], r["avg"], {k: (short(o), "홈" if h else "원") for k, (o, h) in sorted(r["games"].items())})
    print("OK: 2편 표와 일치, 카드 2장 저장")
