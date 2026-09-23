"""
프로젝트 전체에서 쓰는 설정값을 한 곳에 모아둡니다.

왜 이렇게 하나요?
  팀 이름이나 폴더 위치가 여러 파일에 흩어져 있으면,
  나중에 하나만 바꿔도 여러 파일을 뒤져야 합니다.
  실무에서는 이런 값을 '설정 파일' 한 곳에 모으는 것이 기본입니다.
"""

from pathlib import Path

# 프로젝트 최상위 폴더 (src의 부모 폴더)
ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"
CHART_DIR = OUTPUT_DIR / "charts"
POST_DIR = ROOT / "posts"
SITE_DATA_DIR = ROOT / "site" / "data"

# 분석 대상 팀
MY_TEAM = "대구FC"
SEASON = 2026

# 차트 색상 (사이트와 통일해서 한 세트처럼 보이게)
COLOR_MAIN = "#0b5cab"      # 대구FC 블루 계열
COLOR_SUB = "#c9d6e4"       # 비교 대상용 연한 색
COLOR_ACCENT = "#e4572e"    # 강조용

for d in (OUTPUT_DIR, CHART_DIR, POST_DIR, SITE_DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)
