"""
2단계: 분석

이 파일이 프로젝트의 핵심입니다.
데이터포털에도 있는 '단순 합계'가 아니라, 직접 계산해야 나오는 지표를 만듭니다.

기본 분석 (경기 합계 데이터만 있으면 동작)
  1) on_off_analysis   : 특정 선수가 나올 때 / 안 나올 때 팀이 어떻게 달라지나
  2) team_season_table : 팀별 시즌 요약 (승격 경쟁팀 비교용)
  3) player_per90      : 선수별 90분당 기록 (출전 시간이 달라도 공정하게 비교)

심화 분석 (구역별 데이터가 있을 때만 동작, 없으면 None 반환)
  4) ppda_by_match     : PPDA 압박 강도 지표 (+ 점유율 보정)
  5) field_tilt        : 공격 진영 주도권
"""

import pandas as pd

from . import config

# 팀 단위로 비교할 지표들
# (표시이름, 컬럼명, 높을수록 좋은가)
TEAM_METRICS = [
    ("경기당 득점", "goals", True),
    ("패스 성공률(%)", "pass_pct", True),
    ("경기당 슈팅", "shots", True),
    ("경기당 태클", "tackles", True),
    ("경기당 인터셉트", "interceptions", True),
]


def on_off_analysis(data: dict, player: str) -> dict:
    """
    한 선수의 On/Off 분석.

    개념
      '출전한 경기'와 '결장한 경기'로 팀 성적을 나눠서 비교합니다.
      메이저리그/NBA에서 오래 쓰여온 방법이고, 축구에서도 씁니다.

    한계 (글에 반드시 같이 써야 하는 부분)
      - 표본이 작습니다. 결장 경기가 3~4경기면 우연일 수 있습니다.
      - 상대 팀 전력, 홈/원정이 섞여 있습니다.
      - 다른 선수가 같이 빠졌다면 누구 영향인지 구분되지 않습니다.
      => 그래서 '이 선수 덕분이다'가 아니라 '이런 경향이 보인다'로 써야 합니다.
    """
    matches = data["matches"]
    lineups = data["lineups"]
    team = data["team"]

    # 그 선수가 출전한 경기 id 목록
    played_ids = set(lineups.loc[lineups["player"] == player, "match_id"])

    my_team_stats = team[team["team"] == config.MY_TEAM]
    opp_stats = team[team["team"] != config.MY_TEAM]

    def summarize(match_ids):
        m = matches[matches["match_id"].isin(match_ids)]
        mine = my_team_stats[my_team_stats["match_id"].isin(match_ids)]
        opp = opp_stats[opp_stats["match_id"].isin(match_ids)]
        if len(m) == 0:
            return None
        return {
            "경기수": int(len(m)),
            "경기당 승점": round(m["points"].mean(), 2),
            "경기당 득점": round(m["gf"].mean(), 2),
            "경기당 실점": round(m["ga"].mean(), 2),
            "패스 성공률(%)": round(mine["pass_pct"].mean(), 1),
            "경기당 슈팅": round(mine["shots"].mean(), 1),
            # 아래 두 개는 '압박 대체 지표'입니다. 정식 지표인 PPDA는 이벤트를
            # 구역별로 나눈 집계가 있어야 해서, 경기 전체 합계만 있을 때는
            # '상대가 얼마나 편하게 패스했는가'로 간접 측정합니다.
            # (구역별 데이터가 생기면 아래 ppda_by_match()로 정식 계산 가능)
            "상대 패스 성공률(%)": round(opp["pass_pct"].mean(), 1),
            "경기당 수비액션": round(
                (mine["tackles"] + mine["interceptions"] + mine["blocks"]).mean(), 1
            ),
        }

    all_ids = set(matches["match_id"])
    on = summarize(played_ids)
    off = summarize(all_ids - played_ids)

    result = {"player": player, "on": on, "off": off, "diff": None, "warning": None}

    if on and off:
        result["diff"] = {
            k: round(on[k] - off[k], 2) for k in on if k != "경기수"
        }
        # 표본이 작으면 경고를 자동으로 붙입니다 (글 쓸 때 빠뜨리지 않도록)
        smaller = min(on["경기수"], off["경기수"])
        if smaller < 5:
            result["warning"] = (
                f"한쪽 그룹이 {smaller}경기뿐입니다. "
                f"우연일 가능성이 크니 '경향' 수준으로만 해석하세요."
            )
    else:
        result["warning"] = "출전 또는 결장 경기가 없어 비교할 수 없습니다."

    return result


# 사이트와 차트가 기대하는 표 형식 (컬럼 이름을 바꾸면 사이트도 고쳐야 합니다)
SEASON_COLS = ["team", "경기수", "경기당_득점", "패스_성공률", "경기당_슈팅",
               "경기당_유효슈팅", "경기당_태클", "경기당_인터셉트", "유효슈팅_비율"]


def team_season_table(data: dict) -> pd.DataFrame:
    """
    팀별 시즌 요약표. 승격 경쟁팀과 비교할 때 씁니다.
    경기 수가 팀마다 다르므로 전부 '경기당' 평균으로 계산합니다.

    데이터 출처가 두 가지입니다.
      1순위: data/raw/team_season_stats.csv (리그 전체 팀의 시즌 누적)
             -> 대구와 만나지 않은 경기까지 포함되므로 비교가 정확합니다.
      2순위: 대구 경기에서 수집한 양 팀 기록을 집계
             -> 상대팀은 대구전 표본만 있어 왜곡될 수 있습니다.

    이렇게 나눈 이유: 파일이 없어도 프로젝트가 멈추지 않게 하려는 것입니다.
    실무에서 '있으면 더 좋은 데이터'는 이런 식으로 선택 사항으로 둡니다.
    """
    season = data.get("team_season")
    if season is not None and len(season):
        return _season_table_from_totals(season)

    team = data["team"]
    agg = team.groupby("team").agg(
        경기수=("match_id", "count"),
        경기당_득점=("goals", "mean"),
        패스_성공률=("pass_pct", "mean"),
        경기당_슈팅=("shots", "mean"),
        경기당_유효슈팅=("shots_on", "mean"),
        경기당_태클=("tackles", "mean"),
        경기당_인터셉트=("interceptions", "mean"),
    ).round(2).reset_index()

    # 슈팅 대비 유효슈팅 비율 = 마무리 정확도의 간단한 지표
    agg["유효슈팅_비율"] = (agg["경기당_유효슈팅"] / agg["경기당_슈팅"] * 100).round(1)
    agg["출처"] = "대구전 표본"
    return agg.sort_values("경기당_득점", ascending=False)


def _season_table_from_totals(df) -> pd.DataFrame:
    """
    시즌 누적 합계를 '경기당' 평균표로 변환합니다.

    설계 의도: 아직 못 채운 컬럼이 있어도 동작해야 합니다.
      순위·승점·득실은 위키백과나 뉴스로 쉽게 구하지만,
      패스·슈팅·태클 같은 상세 기록은 데이터포털에서 따로 옮겨 적어야 합니다.
      그래서 값이 비어 있는 컬럼은 표에서 아예 빼버립니다.
      (빈 칸이 '-'로 줄줄이 늘어서면 표가 읽기 어려워집니다)
    """
    out = pd.DataFrame({"team": df["team"], "경기수": df["matches"]})
    n = df["matches"].replace(0, pd.NA)

    def has(*cols):
        """그 컬럼들이 존재하고, 값이 하나라도 들어 있는가"""
        return all(c in df.columns and df[c].notna().any() for c in cols)

    # 승격 경쟁을 보는 주제이므로 순위 관련 항목을 앞쪽에 둡니다
    if has("wins", "draws", "losses"):
        out["승"] = df["wins"]
        out["무"] = df["draws"]
        out["패"] = df["losses"]
    if has("points"):
        out["승점"] = df["points"]
        out["경기당_승점"] = (df["points"] / n).round(2)
    if has("goals"):
        out["경기당_득점"] = (df["goals"] / n).round(2)
    if has("goals_against"):
        out["경기당_실점"] = (df["goals_against"] / n).round(2)
    if has("goals", "goals_against"):
        out["득실차"] = df["goals"] - df["goals_against"]

    # 아래는 데이터포털에서 채워야 하는 상세 기록. 비어 있으면 표에 넣지 않습니다.
    if has("pass_att", "pass_cmp"):
        out["패스_성공률"] = (df["pass_cmp"] / df["pass_att"] * 100).round(2)
    if has("shots"):
        out["경기당_슈팅"] = (df["shots"] / n).round(2)
    if has("shots_on"):
        out["경기당_유효슈팅"] = (df["shots_on"] / n).round(2)
    if has("shots", "shots_on"):
        out["유효슈팅_비율"] = (df["shots_on"] / df["shots"] * 100).round(1)
    if has("tackles"):
        out["경기당_태클"] = (df["tackles"] / n).round(2)
    if has("interceptions"):
        out["경기당_인터셉트"] = (df["interceptions"] / n).round(2)

    out["출처"] = "시즌 누적"
    sort_key = "승점" if "승점" in out.columns else "경기당_득점"
    return out.sort_values(sort_key, ascending=False).reset_index(drop=True)



def player_per90(data: dict, min_minutes: int = 180) -> pd.DataFrame:
    """
    선수별 90분당 기록.

    왜 90분당인가?
      A선수가 900분 뛰고 패스 500회, B선수가 300분 뛰고 패스 200회일 때
      단순 합계로 보면 A가 훨씬 많아 보이지만,
      90분당으로 바꾸면 A는 50회, B는 60회로 B가 더 많습니다.
      출전 시간이 다른 선수를 공정하게 비교하려면 반드시 필요한 보정입니다.

    min_minutes: 너무 적게 뛴 선수는 수치가 튀므로 제외합니다.
    """
    lineups = data["lineups"]
    player = data["player"]

    merged = player.merge(
        lineups[["match_id", "player", "position", "minutes", "started"]],
        on=["match_id", "player"], how="left",
    )

    grouped = merged.groupby("player").agg(
        포지션=("position", "first"),
        출전경기=("match_id", "count"),
        선발=("started", "sum"),
        출전시간=("minutes", "sum"),
        패스시도=("pass_att", "sum"),
        패스성공=("pass_cmp", "sum"),
        키패스=("key_pass", "sum"),
        슈팅=("shots", "sum"),
        태클=("tackles", "sum"),
        인터셉트=("interceptions", "sum"),
        경합승리=("duels_won", "sum"),
    ).reset_index()

    grouped = grouped[grouped["출전시간"] >= min_minutes].copy()

    factor = 90 / grouped["출전시간"]
    for col in ["패스시도", "키패스", "슈팅", "태클", "인터셉트", "경합승리"]:
        grouped[f"{col}_per90"] = (grouped[col] * factor).round(2)

    grouped["패스성공률"] = (grouped["패스성공"] / grouped["패스시도"] * 100).round(1)
    return grouped.sort_values("출전시간", ascending=False)


# ---------------------------------------------------------------------------
# PPDA (Passes Per Defensive Action) — 압박 강도 지표
# ---------------------------------------------------------------------------
#
# 개념
#   상대가 '자기 진영 + 중앙 지역'(피치의 약 60% 구역)에서 패스를 시도할 때,
#   우리 팀이 수비 액션(태클·인터셉트·파울·클리어링) 하나를 하기까지
#   평균 몇 번의 패스를 허용했는가.
#
#       PPDA = 허용한 상대 패스 수 ÷ 우리 팀 수비 액션 수
#
#   낮을수록 강한 전방 압박 (4~5 = 리버풀식 강한 압박)
#   높을수록 물러서서 지키는 로우 블록 (15~20)
#
# 중요한 오해 정정
#   "PPDA는 좌표 데이터가 없어도 계산할 수 있다"는 말은 절반만 맞습니다.
#   전체 x,y 좌표는 필요 없지만, **이벤트를 구역(zone)별로 나눈 집계**는 반드시 필요합니다.
#   경기 전체 합계만 있으면 계산할 수 없습니다.
#
#   따라서 이 함수는 CSV에 아래 '선택 컬럼'이 있을 때만 정식 PPDA를 계산하고,
#   없으면 None을 돌려줍니다. (대체 지표는 on_off_analysis가 이미 제공)
#
#     team_match_stats.csv 선택 컬럼
#       opp_pass_att_def60 : 상대가 자기 진영+중앙(60% 구역)에서 시도한 패스 수
#       def_action_att60   : 우리 팀이 그 구역에서 한 수비 액션 수
#                            (태클 + 인터셉트 + 파울 + 클리어링)
#
# 알려진 한계
#   - 압박을 '시도'한 횟수만 셀 뿐, 실제로 공을 뺏었는지는 반영하지 않습니다.
#   - 점유율이 높은 팀은 상대가 공을 가진 시간 자체가 짧아 분모가 줄고,
#     그 결과 PPDA가 실제보다 높게(=약한 압박처럼) 보이는 왜곡이 생깁니다.
#     → 아래 possession_adjusted=True 로 점유율 보정을 할 수 있습니다.

PPDA_COLS = ("opp_pass_att_def60", "def_action_att60")


def has_ppda_columns(data: dict) -> bool:
    """PPDA를 계산할 수 있는 구역별 컬럼이 준비돼 있는지 확인"""
    return all(c in data["team"].columns for c in PPDA_COLS)


def ppda_by_match(data: dict, possession_adjusted: bool = False):
    """
    경기별 PPDA를 계산합니다. 컬럼이 없으면 None을 반환합니다.

    possession_adjusted=True 이면 점유율로 보정합니다.
      보정식: PPDA x (우리 점유율 / 50)
      점유율이 높아 분모가 작아지는 왜곡을 완화하려는 간단한 보정입니다.
      (업계 표준이 하나로 정해져 있지는 않습니다. 글에 보정 방식을 밝히세요.)
    """
    if not has_ppda_columns(data):
        return None

    team = data["team"]
    mine = team[team["team"] == config.MY_TEAM].copy()

    mine["ppda"] = (
        mine["opp_pass_att_def60"] / mine["def_action_att60"].replace(0, pd.NA)
    ).round(2)

    if possession_adjusted and "possession" in mine.columns:
        mine["ppda_adj"] = (mine["ppda"] * mine["possession"] / 50).round(2)

    return mine[["match_id", "team", "ppda"] +
                (["ppda_adj"] if "ppda_adj" in mine.columns else [])]


def field_tilt(data: dict):
    """
    필드 틸트(Field Tilt) — 빌드업 주도권의 대체 지표.

    개념: 공격 진영(attacking third)에서 일어난 패스 중 우리 팀이 차지한 비율.
          점유율과 달리 '위험한 지역에서 누가 공을 돌렸는가'를 봅니다.

          필드 틸트 = 우리 공격진영 패스 / (우리 + 상대 공격진영 패스) x 100

    선택 컬럼 `pass_att_final3`(공격 진영 패스 시도)가 양 팀 모두 있어야 계산됩니다.
    """
    team = data["team"]
    if "pass_att_final3" not in team.columns:
        return None

    pivot = team.pivot_table(index="match_id", columns="team",
                             values="pass_att_final3", aggfunc="sum")
    if config.MY_TEAM not in pivot.columns:
        return None

    mine = pivot[config.MY_TEAM]
    others = pivot.drop(columns=[config.MY_TEAM]).sum(axis=1)
    return ((mine / (mine + others)) * 100).round(1).rename("field_tilt").reset_index()
