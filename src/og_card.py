"""
링크 미리보기 카드(og:image) 만들기 → site/img/og_card.png (1200x630)

카톡·네이버·블로그에 사이트 주소를 붙이면 이 그림이 썸네일로 뜹니다.
숫자는 손으로 적지 않고 site/data/standings.js, fixtures.js 에서 읽습니다.
그래서 `python run.py standings` 를 돌릴 때마다 같이 다시 만들어집니다.

규칙
  - 사실만 적습니다(순위·승점·다음 경기). 해석 문장 없음.
  - 엠블럼·선수 사진 없음. 출처 문구를 항상 넣습니다.
  - 색·글꼴은 card_style.py 를 그대로 씁니다(카드 스타일을 한 곳에서 관리).

크기: 1200x630 은 페이스북/카카오가 권장하는 1.91:1 비율입니다.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from src import card_style as cs
from src import config

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = config.ROOT / "site" / "img" / "og_card.png"
WEEKDAY = "월화수목금토일"


def _load(name: str) -> dict:
    """site/data/<name>.js (window.X = {JSON};) 를 dict 로."""
    text = (config.SITE_DATA_DIR / f"{name}.js").read_text(encoding="utf-8")
    body = re.split(r"window\.\w+\s*=\s*", text, maxsplit=1)[1].strip().rstrip(";")
    return json.loads(body)


def _next_match(fixtures: list[dict], team: str, as_of: str) -> dict | None:
    """기준일 다음 날 이후 첫 경기. 일정표가 비면 None."""
    games = sorted((f for f in fixtures if team in (f["home"], f["away"]) and f["date"] > as_of),
                   key=lambda f: f["date"])
    return games[0] if games else None


def _match_text(f: dict, team: str) -> str:
    d = dt.date.fromisoformat(f["date"])
    home = f["home"] == team
    opp = f["away"] if home else f["home"]
    time = f" {f['time']}" if f.get("time") else ""
    return f"{d.month}/{d.day}({WEEKDAY[d.weekday()]}){time}  vs {opp} ({'홈' if home else '원정'})"


def make_og_card() -> Path:
    st = _load("standings")
    meta, teams = st["meta"], st["teams"]
    team = meta.get("team", config.MY_TEAM)
    me = next(t for t in teams if t["team"] == team)
    nxt = _next_match(_load("fixtures")["fixtures"], team, meta["as_of"])

    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=cs.SURFACE)

    # ---- 왼쪽: 사이트 이름 + 우리 팀 현재 위치
    fig.text(0.06, 0.86, cs.SITE_NAME, fontsize=22, color=cs.FOCUS, weight="bold")
    fig.text(0.06, 0.77, "K리그2 데이터로 읽는 대구FC", fontsize=18, color=cs.TEXT_2)
    fig.text(0.06, 0.53, f"{me['총점순위']}위", fontsize=72, color=cs.TEXT_1, weight="bold")
    x_pts = 0.255 if me["총점순위"] < 10 else 0.32  # 두 자리 순위면 글자가 겹치지 않게 오른쪽으로
    fig.text(x_pts, 0.555, f"승점 {me['승점']}", fontsize=34, color=cs.TEXT_1, weight="bold")
    fig.text(0.06, 0.44, f"{me['경기수']}경기 {me['승']}승 {me['무']}무 {me['패']}패 · 득실 {me['득실차']:+d}",
             fontsize=18, color=cs.TEXT_2)
    if nxt:
        fig.text(0.06, 0.31, "다음 경기", fontsize=15, color=cs.TEXT_3)
        fig.text(0.06, 0.24, _match_text(nxt, team), fontsize=20, color=cs.TEXT_1, weight="bold")

    # ---- 오른쪽: 상위 6팀 (우리 팀만 파랑, 나머지 회색 — 강조색 1개 규칙)
    ax = fig.add_axes([0.60, 0.20, 0.34, 0.66])
    ax.axis("off")
    ax.set_xlim(0, 1)
    top = sorted(teams, key=lambda t: t["총점순위"])[:6]
    if me not in top:
        top = top[:5] + [me]
    n = len(top)
    ax.set_ylim(0, n)
    for i, t in enumerate(top):
        y = n - i - 0.5
        mine = t["team"] == team
        if mine:
            ax.add_patch(FancyBboxPatch((0, y - 0.38), 1, 0.76, boxstyle="round,pad=0,rounding_size=0.08",
                                        facecolor="#e6f0fb", edgecolor="none"))
        col = cs.FOCUS if mine else cs.TEXT_2
        w = "bold" if mine else "normal"
        ax.text(0.05, y, f"{t['총점순위']}", fontsize=17, color=col, weight=w, va="center")
        ax.text(0.17, y, t["team"], fontsize=17, color=cs.TEXT_1 if mine else cs.TEXT_2, weight=w, va="center")
        ax.text(0.95, y, f"{t['승점']}", fontsize=17, color=col, weight="bold", va="center", ha="right")
    fig.text(0.60, 0.88, "순위 · 승점", fontsize=14, color=cs.TEXT_3)

    # ---- 바닥글: 기준일 + 출처 (항상)
    fig.text(0.06, 0.07, f"{meta['as_of']} 기준 · {meta.get('as_of_note', '')}   |   {cs.COPYRIGHT}",
             fontsize=12, color=cs.TEXT_3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=100, facecolor=cs.SURFACE)  # bbox 조정 안 함: 1200x630 크기를 정확히 유지
    plt.close(fig)
    print(f"  미리보기 카드 -> {OUT}")
    return OUT


if __name__ == "__main__":
    make_og_card()
