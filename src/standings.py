"""
순위표 분석 (연재 1편 "승격 경쟁팀, 숫자로 줄 세워보기" 전용)

설계 의도
---------
이 파일은 team_season_stats.csv 한 장만 있으면 돌아갑니다.
선수 기록, 경기별 기록이 전혀 없어도 됩니다.

왜 따로 떼어냈나요?
  analyze.py 는 '대구 경기 기록'을 다루는 곳이고,
  여기는 '리그 17팀 순위표'를 다루는 곳입니다.
  다루는 데이터의 단위가 다르면 파일을 나누는 것이 실무 관행입니다.
  나중에 1편만 다시 돌리고 싶을 때 이 파일만 보면 됩니다.

핵심 개념 3가지
  1) PPG (Points Per Game, 경기당 승점)
     팀마다 소화 경기 수가 다르면 총 승점 비교는 착시입니다.
     25경기 48점과 26경기 48점은 같은 성적이 아닙니다.

  2) 잔차 (Residual)
     '경기당 득실차'로 '경기당 승점'을 예측하는 직선을 그은 뒤,
     실제 승점이 그 직선보다 위면 +, 아래면 -.
     "내용에 비해 승점을 더 벌었는가"를 보는 지표입니다.
     ※ 잔차의 '원인'은 이 데이터로 알 수 없습니다. 관측만 하세요.

  3) 시나리오 (Scenario)
     확률 모델이 아닙니다. 단순 뺄셈입니다.
     "경쟁팀이 남은 경기에서 X점을 따면 우리는 몇 점이 필요한가".
     가정이 적을수록 반박당할 곳도 적습니다.
"""

import pandas as pd

from . import config, load

# ---------------------------------------------------------------------------
# 리그 구조 설정
# ---------------------------------------------------------------------------
# K리그2 2026: 17팀 2로빈(모든 팀과 홈/원정 1번씩) = 팀당 32경기
# [출처: 사용자 확인 / 연맹 공식 규정으로 재확인 권장]
TEAMS = 17
TOTAL_MATCHES_PER_TEAM = (TEAMS - 1) * 2   # 32

# 자동 승격 순위 (1~2위). 3~6위는 승격 플레이오프.
AUTO_PROMOTION_RANK = 2

WIN_POINTS = 3

# 잔차가 이 값(표준편차의 배수) 이상일 때만 "의미 있다"고 표시합니다.
# 1.5σ 미만은 표본 17개에서 노이즈와 구분되지 않습니다.
SIGMA_THRESHOLD = 1.5


# ---------------------------------------------------------------------------
# 1) 경기당 승점 보정표
# ---------------------------------------------------------------------------
def ppg_table(season: pd.DataFrame) -> pd.DataFrame:
    """
    총 승점 순위표에 '경기당' 지표를 덧붙이고, PPG 기준으로 다시 정렬합니다.

    반환 컬럼
      team, matches, points, 득실차, 경기당승점, 경기당득실차,
      잔여경기, 최대가능승점, 총점순위, PPG순위, 순위변동
    """
    df = season.copy()

    df["득실차"] = df["goals"] - df["goals_against"]
    df["경기당승점"] = (df["points"] / df["matches"]).round(3)
    df["경기당득점"] = (df["goals"] / df["matches"]).round(2)
    df["경기당실점"] = (df["goals_against"] / df["matches"]).round(2)
    df["경기당득실차"] = (df["득실차"] / df["matches"]).round(3)

    df["잔여경기"] = TOTAL_MATCHES_PER_TEAM - df["matches"]
    df["최대가능승점"] = df["points"] + df["잔여경기"] * WIN_POINTS

    # 총점 순위: 승점 -> 다득점 -> 득실차
    #
    # 순서가 중요합니다. K리그는 '다득점'이 '득실차'보다 먼저입니다.
    #   예) 충북청주(29점, 31득점, -10) vs 파주(29점, 24득점, -4)
    #       득실차 우선이면 파주가 위지만, 실제 순위는 청주가 위입니다.
    # 흔한 실수: 유럽 리그 습관대로 득실차를 먼저 넣는 것.
    # 실제 규정에는 승자승 등 추가 조건이 있으므로 동점 팀 순서는 참고용입니다.
    df = df.sort_values(["points", "goals", "득실차"], ascending=False).reset_index(drop=True)
    df["총점순위"] = range(1, len(df) + 1)

    df = df.sort_values("경기당승점", ascending=False).reset_index(drop=True)
    df["PPG순위"] = range(1, len(df) + 1)

    df["순위변동"] = df["총점순위"] - df["PPG순위"]   # +면 PPG 보정으로 상승

    return df


# ---------------------------------------------------------------------------
# 2) 경기당 득실차 -> 경기당 승점 단순회귀
# ---------------------------------------------------------------------------
def gd_regression(table: pd.DataFrame) -> dict:
    """
    최소제곱 단순회귀를 직접 계산합니다.

    왜 라이브러리(scipy/sklearn)를 안 쓰나요?
      의존성을 하나 늘리는 것보다, 식이 4줄이면 직접 쓰는 편이
      나중에 "이 숫자가 어디서 나왔지?" 를 추적하기 쉽습니다.
      실무에서도 이 정도 계산은 직접 쓰는 경우가 많습니다.

    반환
      slope, intercept, r2, resid_sd, table(잔차 컬럼 추가됨)
    """
    df = table.copy()
    x = df["경기당득실차"]
    y = df["경기당승점"]
    n = len(df)

    mx, my = x.mean(), y.mean()
    slope = ((x - mx) * (y - my)).sum() / ((x - mx) ** 2).sum()
    intercept = my - slope * mx

    pred = intercept + slope * x
    resid = y - pred

    ss_tot = ((y - my) ** 2).sum()
    ss_res = (resid ** 2).sum()
    r2 = 1 - ss_res / ss_tot

    # 자유도 n-2 (기울기와 절편 2개를 추정했으므로)
    resid_sd = (ss_res / (n - 2)) ** 0.5

    df["예측승점"] = pred.round(3)
    df["잔차"] = resid.round(3)
    df["잔차_시즌환산"] = (resid * df["matches"]).round(1)   # 지금까지 더/덜 번 승점
    df["시그마"] = (resid / resid_sd).round(2)
    df["유의"] = df["시그마"].abs() >= SIGMA_THRESHOLD

    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r2": round(r2, 3),
        "resid_sd": round(resid_sd, 4),
        "table": df.sort_values("잔차", ascending=False).reset_index(drop=True),
    }


# ---------------------------------------------------------------------------
# 3) 자동 승격(2위) 추격 시나리오
# ---------------------------------------------------------------------------
def race_scenario(table: pd.DataFrame, team: str = None) -> dict:
    """
    우리 팀이 자동 승격권(2위) 안에 들려면 남은 경기에서 몇 점이 필요한가.

    확률이 아니라 산술입니다.
      경쟁팀이 잔여 경기에서 P점을 딴다고 '가정'했을 때,
      우리가 그 팀을 넘으려면 몇 점이 필요한지 표로 보여줍니다.
      가정을 독자가 직접 고를 수 있게 하는 것이 요점입니다.
    """
    team = team or config.MY_TEAM
    t = table.set_index("team")

    if team not in t.index:
        raise KeyError(f"'{team}' 이 team_season_stats.csv 에 없습니다.")

    me = t.loc[team]
    my_left = int(me["잔여경기"])
    my_pts = int(me["points"])
    my_max = my_pts + my_left * WIN_POINTS

    # 현재 총점 순위 기준 1~2위 팀 (= 넘어야 할 대상)
    top = table.sort_values("총점순위").head(AUTO_PROMOTION_RANK)
    rivals = [r for r in top["team"].tolist() if r != team]

    # 직접 경쟁 대상은 '2위 팀' (1위를 넘으려면 2위도 넘어야 하므로)
    key_rival = rivals[-1] if rivals else None

    rows = []
    if key_rival:
        rv = t.loc[key_rival]
        rv_left = int(rv["잔여경기"])
        rv_pts = int(rv["points"])

        # 경쟁팀의 잔여 승점을 0부터 전승까지 3점 단위로 훑습니다
        for gained in range(0, rv_left * WIN_POINTS + 1, WIN_POINTS):
            rival_final = rv_pts + gained
            need = rival_final - my_pts + 1          # '넘어서려면' 1점 더
            possible = need <= my_left * WIN_POINTS
            rows.append({
                f"{key_rival} 잔여승점": gained,
                f"{key_rival} 최종": rival_final,
                f"{team} 필요승점": max(need, 0),
                "필요 최소 승수(무승부 0 가정)": -(-max(need, 0) // WIN_POINTS),
                "산술적 가능": "O" if possible else "X",
            })

    # 현재 페이스(PPG)가 그대로 유지될 경우의 최종 승점 추정
    pace = {}
    for name in [team] + rivals:
        row = t.loc[name]
        final = row["points"] + row["경기당승점"] * row["잔여경기"]
        pace[name] = round(final, 1)

    return {
        "team": team,
        "현재승점": my_pts,
        "잔여경기": my_left,
        "최대가능승점": my_max,
        "경쟁팀": rivals,
        "핵심경쟁팀": key_rival,
        "시나리오표": pd.DataFrame(rows),
        "현재페이스_최종승점": pace,
    }


# ---------------------------------------------------------------------------
# 실행 진입점
# ---------------------------------------------------------------------------
def run(team: str = None) -> dict:
    """python run.py standings 로 호출됩니다."""
    from . import charts, export

    team = team or config.MY_TEAM

    season = load.read_team_season()
    if season is None:
        print("[중단] data/raw/team_season_stats.csv 가 없습니다.")
        return {}

    print(f"\n[1/4] 경기당 승점 보정 중... ({len(season)}팀)")
    table = ppg_table(season)
    changed = table[table["순위변동"] != 0]
    print(f"  PPG 보정으로 순위가 바뀐 팀: {len(changed)}개")

    print("\n[2/4] 득실차 대비 승점 회귀 중...")
    reg = gd_regression(table)
    print(f"  PPG = {reg['intercept']} + {reg['slope']} x 경기당득실차")
    print(f"  R2 = {reg['r2']}  (1에 가까울수록 득실차가 승점을 잘 설명)")
    print(f"  잔차 표준편차 = {reg['resid_sd']} PPG")
    sig = reg["table"][reg["table"]["유의"]]
    print(f"  {SIGMA_THRESHOLD}σ 이상 벗어난 팀: {', '.join(sig['team']) if len(sig) else '없음'}")

    print("\n[3/4] 자동 승격 시나리오 계산 중...")
    race = race_scenario(table, team)
    print(f"  {team}: {race['현재승점']}점, 잔여 {race['잔여경기']}경기, "
          f"최대 {race['최대가능승점']}점")

    print("\n[4/4] 차트 + 초안 만드는 중...")
    charts.setup_korean_font()

    # '대패 왜곡' 사례 자동 선정:
    #   득실차 순위는 바닥권인데 잔차 순위는 상위권인 팀.
    #   글의 한계 섹션에서 이름을 언급하므로 차트에도 라벨이 있어야 합니다.
    rt = reg["table"].copy()
    rt["득실차순위"] = rt["경기당득실차"].rank(ascending=False)
    rt["잔차순위"] = rt["잔차"].rank(ascending=False)
    rt["괴리"] = rt["득실차순위"] - rt["잔차순위"]
    distortion = rt.sort_values("괴리", ascending=False).iloc[0]["team"]
    print(f"  대패 왜곡 사례(자동 선정): {distortion}")
    race["왜곡사례"] = distortion   # 초안 5번 섹션에서 이름으로 언급합니다

    chart_path = charts.chart_standings_regression(reg, team,
                                                   highlight=[distortion])
    export.export_standings_json(table, reg, race)
    post_path = export.export_standings_post(table, reg, race, chart_path)

    print("\n" + "=" * 50)
    print("완료!")
    print(f"  차트 -> {chart_path}")
    print(f"  초안 -> {post_path}   ((빈칸)을 직접 채우세요)")
    print("=" * 50)

    return {"table": table, "regression": reg, "race": race}
