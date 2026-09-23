"""
3단계: 차트 만들기 (블로그에 붙여넣을 PNG)

흔한 함정: matplotlib은 기본 설정에서 한글이 네모(□□□)로 깨집니다.
아래 setup_korean_font()가 시스템에 설치된 한글 폰트를 찾아서 자동으로 설정합니다.
"""

import matplotlib

matplotlib.use("Agg")  # 화면 없이 파일로만 저장 (서버/자동화 환경에서 필수)

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from . import config

# 운영체제별로 흔히 설치돼 있는 한글 폰트 후보
KOREAN_FONT_CANDIDATES = [
    "Malgun Gothic",      # Windows
    "AppleGothic",        # macOS
    "NanumGothic",        # 나눔고딕 (설치했다면)
    "Noto Sans CJK KR",   # Linux
    "Noto Sans KR",
]


def setup_korean_font() -> bool:
    """설치된 한글 폰트를 찾아 matplotlib에 적용. 찾으면 True."""
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in KOREAN_FONT_CANDIDATES:
        if name in installed:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지
            return True
    print("[경고] 한글 폰트를 찾지 못했습니다. 차트의 한글이 깨질 수 있습니다.")
    print("       Windows라면 보통 'Malgun Gothic'이 이미 있습니다.")
    return False


def _save(fig, filename: str) -> str:
    path = config.CHART_DIR / filename
    # dpi=150 : 블로그에 올렸을 때 흐려지지 않을 정도의 해상도
    # bbox_inches='tight' : 글자가 잘리지 않게 여백 자동 조정
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  차트 저장: {path.name}")
    return str(path)


def chart_on_off(result: dict) -> str | None:
    """On/Off 비교 막대 차트"""
    if not result.get("on") or not result.get("off"):
        return None

    keys = ["경기당 승점", "경기당 득점", "경기당 실점", "패스 성공률(%)"]
    on_vals = [result["on"][k] for k in keys]
    off_vals = [result["off"][k] for k in keys]

    fig, axes = plt.subplots(1, len(keys), figsize=(3 * len(keys), 3.6))
    for ax, key, on_v, off_v in zip(axes, keys, on_vals, off_vals):
        ax.bar(["출전", "결장"], [on_v, off_v],
               color=[config.COLOR_MAIN, config.COLOR_SUB], width=0.55)
        ax.set_title(key, fontsize=11)
        for i, v in enumerate([on_v, off_v]):
            ax.text(i, v, f"{v}", ha="center", va="bottom", fontsize=10)
        ax.set_ylim(0, max(on_v, off_v) * 1.25 + 0.1)
        ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle(f"{result['player']} 출전 / 결장 경기 비교", fontsize=13, y=1.02)
    return _save(fig, f"onoff_{result['player']}.png")


def chart_team_compare(table, teams: list[str], metric: str = "경기당_득점") -> str:
    """팀 비교 가로 막대 차트"""
    sub = table[table["team"].isin(teams)].sort_values(metric)
    colors = [config.COLOR_MAIN if t == config.MY_TEAM else config.COLOR_SUB
              for t in sub["team"]]

    fig, ax = plt.subplots(figsize=(7, 0.55 * len(sub) + 1.5))
    ax.barh(sub["team"], sub[metric], color=colors, height=0.6)
    for y, v in enumerate(sub[metric]):
        ax.text(v, y, f" {v}", va="center", fontsize=10)
    ax.set_title(f"{metric.replace('_', ' ')} 비교", fontsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, f"team_{metric}.png")


def chart_player_trend(data: dict, player: str, metric: str = "pass_pct") -> str | None:
    """한 선수의 경기별 흐름 선 차트"""
    df = data["player"]
    sub = df[df["player"] == player].merge(
        data["matches"][["match_id", "round", "opponent"]], on="match_id"
    ).sort_values("round")

    if sub.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(sub["round"], sub[metric], marker="o", color=config.COLOR_MAIN)
    mean = sub[metric].mean()
    ax.axhline(mean, ls="--", color=config.COLOR_ACCENT, lw=1,
               label=f"평균 {mean:.1f}")
    ax.set_xlabel("라운드")
    ax.set_title(f"{player} · 경기별 패스 성공률(%)", fontsize=12)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    return _save(fig, f"trend_{player}.png")


def chart_standings_regression(reg: dict, my_team: str = None,
                                highlight: list = None) -> str:
    """
    경기당 득실차 -> 경기당 승점 회귀 산점도 (연재 1편용)

    설계 의도
      - 라벨을 전부 붙이면 글자가 겹쳐서 읽을 수 없습니다.
        통계적으로 의미 있는 팀(1.5σ 이상)과 우리 팀만 이름을 답니다.
      - ±1σ 점선 밴드를 함께 그립니다.
        "이 밴드 안이면 추세선 위/아래를 논할 수 없다"는 것을
        독자가 눈으로 바로 알 수 있게 하기 위함입니다.
      - highlight: 글에서 직접 언급하는 팀(예: 대패 왜곡 사례)은
        1.5σ 미만이라도 라벨을 달아야 글 내용과 그림이 어긋나지 않습니다.
    """
    my_team = my_team or config.MY_TEAM
    highlight = set(highlight or [])
    df = reg["table"]
    sd = reg["resid_sd"]

    fig, ax = plt.subplots(figsize=(8, 5.5))

    # 추세선과 ±1σ 밴드
    xs = [df["경기당득실차"].min() - 0.1, df["경기당득실차"].max() + 0.1]
    ys = [reg["intercept"] + reg["slope"] * x for x in xs]
    ax.plot(xs, ys, color="#888888", lw=1.2, zorder=1,
            label=f"추세선 (R²={reg['r2']})")
    ax.fill_between(xs, [y - sd for y in ys], [y + sd for y in ys],
                    color="#888888", alpha=0.12, zorder=0,
                    label=f"±1σ ({sd:.3f} PPG)")

    # 점 색: 우리 팀 / 유의미한 팀 / 나머지
    for _, r in df.iterrows():
        if r["team"] == my_team:
            color, size, z = config.COLOR_MAIN, 130, 4
        elif r["유의"]:
            color, size, z = config.COLOR_ACCENT, 90, 3
        else:
            color, size, z = config.COLOR_SUB, 60, 2
        ax.scatter(r["경기당득실차"], r["경기당승점"],
                   s=size, color=color, edgecolor="white", lw=1, zorder=z)

        # 라벨은 우리 팀, 유의미한 팀, 글에서 직접 언급하는 팀에만
        if r["team"] == my_team or r["유의"] or r["team"] in highlight:
            ax.annotate(f"{r['team']} ({r['시그마']:+.1f}σ)",
                        (r["경기당득실차"], r["경기당승점"]),
                        textcoords="offset points", xytext=(8, 4),
                        fontsize=9, zorder=5)

    ax.set_xlabel("경기당 득실차")
    ax.set_ylabel("경기당 승점 (PPG)")
    ax.set_title("경기 수를 보정하면, 순위와 내용은 얼마나 일치하는가", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)

    return _save(fig, "standings_regression.png")
