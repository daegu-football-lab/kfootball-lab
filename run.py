"""
전체 파이프라인 실행기

사용법
  python run.py                 # 세징야 기준으로 전체 실행
  python run.py 한국영           # 다른 선수로 실행
  python run.py standings       # 순위표 분석만 실행 (연재 1편용)

하는 일
  데이터 읽기 -> 분석 -> 차트 PNG -> 사이트 JSON -> 블로그 글 초안
"""

import sys

from src import analyze, charts, config, export, load


def main(target_player: str = "세징야"):
    print("=" * 50)
    print(f"{config.MY_TEAM} {config.SEASON} 분석 파이프라인")
    print("=" * 50)

    print("\n[1/5] 데이터 읽는 중...")
    data = load.load_all()
    print(f"  경기 {len(data['matches'])}건, 선수 기록 {len(data['player'])}건")

    print("\n[2/5] On/Off 분석 중...")
    result = analyze.on_off_analysis(data, target_player)
    if not result["on"]:
        print(f"  '{target_player}' 기록이 없습니다. 이름을 확인하세요.")
        return
    print(f"  출전 {result['on']['경기수']}경기 / 결장 {result['off']['경기수']}경기")
    if result["warning"]:
        print(f"  [주의] {result['warning']}")

    print("\n[3/5] 차트 만드는 중...")
    charts.setup_korean_font()
    chart_paths = []
    for maker in (
        lambda: charts.chart_on_off(result),
        lambda: charts.chart_player_trend(data, target_player),
    ):
        p = maker()
        if p:
            chart_paths.append(p)

    team_table = analyze.team_season_table(data)
    top_teams = team_table["team"].head(6).tolist()
    if config.MY_TEAM not in top_teams:
        top_teams.append(config.MY_TEAM)
    chart_paths.append(charts.chart_team_compare(team_table, top_teams))

    ppda = analyze.ppda_by_match(data)
    if ppda is not None:
        print(f"  PPDA 평균: {ppda['ppda'].mean():.2f} (낮을수록 강한 전방 압박)")
    else:
        print("  PPDA: 구역별 컬럼이 없어 건너뜁니다 (대체 지표로 분석)")

    print("\n[4/5] 사이트 데이터 내보내는 중...")
    export.export_site_json(data)

    print("\n[5/5] 블로그 글 초안 만드는 중...")
    export.export_post_draft(result, chart_paths)

    print("\n" + "=" * 50)
    print("완료!")
    print("  차트   -> output/charts/")
    print("  초안   -> posts/   (해석을 직접 채워 넣으세요)")
    print("  사이트 -> site/index.html 을 브라우저로 열어보세요")
    print("=" * 50)


def main_standings():
    """연재 1편용: 순위표(team_season_stats.csv)만으로 돌아가는 분석."""
    from src import standings

    print("=" * 50)
    print(f"K리그2 {config.SEASON} 순위표 분석 (연재 1편)")
    print("=" * 50)
    standings.run()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "세징야"

    # 첫 번째 인자가 'standings' 면 순위표 분석만 돌립니다.
    # 선수 이름과 명령어를 같은 자리에서 받는 단순한 구조입니다.
    # (나중에 명령이 늘어나면 argparse 로 바꾸는 것이 실무 관행입니다.)
    if arg == "standings":
        main_standings()
    else:
        main(arg)
