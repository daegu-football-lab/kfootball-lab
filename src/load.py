"""
1단계: 데이터 불러오기

설계 의도 (중요)
---------------
지금은 CSV 파일에서 읽지만, 나중에 K리그 API 인증키가 생기면
'read_*' 함수 안쪽만 API 호출로 바꾸면 됩니다.
analyze.py, charts.py 등 나머지 코드는 한 줄도 안 바뀝니다.

이것을 실무에서 '데이터 소스 분리' 또는 '어댑터 패턴'이라고 부릅니다.
데이터를 어디서 가져오는지(How)와 그걸로 뭘 하는지(What)를 떼어놓는 것입니다.
"""

import pandas as pd

from . import config


def _read_csv(name: str) -> pd.DataFrame:
    path = config.RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 가 없습니다.\n"
            f"먼저 `python data/make_sample_data.py` 를 실행하거나,\n"
            f"직접 만든 CSV를 data/raw/ 에 넣어주세요."
        )
    # encoding='utf-8-sig' : 엑셀에서 저장한 한글 CSV도 안전하게 읽힙니다
    return pd.read_csv(path, encoding="utf-8-sig")


def read_matches() -> pd.DataFrame:
    """경기 목록: match_id, date, round, home_team, away_team, home_score, away_score"""
    df = _read_csv("matches.csv")

    # 우리 팀 관점으로 컬럼을 추가해 둡니다 (매번 계산하지 않도록)
    is_home = df["home_team"] == config.MY_TEAM
    df["opponent"] = df["away_team"].where(is_home, df["home_team"])
    df["venue"] = is_home.map({True: "홈", False: "원정"})
    df["gf"] = df["home_score"].where(is_home, df["away_score"])   # 득점
    df["ga"] = df["away_score"].where(is_home, df["home_score"])   # 실점
    df["points"] = df.apply(
        lambda r: 3 if r["gf"] > r["ga"] else (1 if r["gf"] == r["ga"] else 0), axis=1
    )
    return df


def read_lineups() -> pd.DataFrame:
    """출전 기록: match_id, player, position, started(1/0), minutes"""
    return _read_csv("lineups.csv")


def read_team_stats() -> pd.DataFrame:
    """팀 단위 경기 기록 (양 팀 모두)"""
    df = _read_csv("team_match_stats.csv")
    # 패스 성공률은 원본에 없으므로 여기서 계산해 둡니다
    df["pass_pct"] = (df["pass_cmp"] / df["pass_att"] * 100).round(1)
    return df


def read_player_stats() -> pd.DataFrame:
    """선수 단위 경기 기록"""
    df = _read_csv("player_match_stats.csv")
    df["pass_pct"] = (df["pass_cmp"] / df["pass_att"].replace(0, pd.NA) * 100).round(1)
    return df


def read_team_season() -> "pd.DataFrame | None":
    """
    (선택) 리그 전체 팀의 '시즌 누적' 기록.

    왜 따로 두나요?
      대구 경기를 아무리 많이 입력해도, 대구와 만나지 않은 경기의
      경쟁팀 기록은 알 수 없습니다. 승격 경쟁팀을 제대로 비교하려면
      각 팀의 시즌 누적 기록이 따로 필요합니다.

      데이터포털의 '팀 기록' 화면을 보고 팀당 한 줄씩만 옮겨 적으면 됩니다.
      (10여 개 팀이면 20분 정도. 한 달에 한 번만 갱신해도 충분합니다.)

    파일이 없으면 None을 반환하고, 코드는 대구 경기 기록만으로 비교합니다.

    data/raw/team_season_stats.csv 컬럼
      team, matches, goals, goals_against, points,
      pass_att, pass_cmp, shots, shots_on, tackles, interceptions
    """
    path = config.RAW_DIR / "team_season_stats.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def load_all() -> dict:
    """네 종류를 한 번에 불러옵니다."""
    return {
        "matches": read_matches(),
        "lineups": read_lineups(),
        "team": read_team_stats(),
        "player": read_player_stats(),
        "team_season": read_team_season(),   # 없으면 None
    }

