"""
슬라이드형 차트 카드(16:9, 1600x900)의 공통 스타일을 한 곳에서 관리합니다.

왜 따로 두나요?
  카드마다 색·글꼴·바닥글을 복사해 넣으면, 사이트 주소 하나만 바뀌어도
  모든 카드 스크립트를 고쳐야 합니다. 스타일은 여기, 그림 내용은 카드별 함수에 둡니다.
규칙 원본: 프로젝트 문서 00번 0절, 39번.
"""
import matplotlib
matplotlib.use("Agg")  # 창을 띄우지 않고 파일로만 저장
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# ---- 색 (강조 1개만 파랑, 나머지 회색. 무지개 금지)
SURFACE = "#fcfcfb"
# TEXT_3(보조 글자)은 배경 대비 4.5:1 이상이 되도록 진하게 (10/4: 블로그에서 흐리게 보여 #8a8984 → #6b6a65)
TEXT_1, TEXT_2, TEXT_3 = "#0b0b0b", "#4a4946", "#6b6a65"
FOCUS = "#2a78d6"
MUTED = "#b9b8b2"
TRACK = "#ebeae6"

SITE_NAME = "대구 풋볼 랩"
SITE_URL = "daegu-football-lab.github.io/kfootball-lab/site"
COPYRIGHT = "데이터 저작권 및 소유권: 한국프로축구연맹(K LEAGUE)"

# 사용자 PC(Windows)는 맑은 고딕, 원격 작업공간(Linux)은 Noto. 먼저 찾은 것을 씁니다.
_FONT_CANDIDATES = ["Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"]


def _pick_font():
    for path in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]:
        try:
            fm.fontManager.addfont(path)
        except Exception:
            pass  # Windows에는 이 경로가 없음 → 맑은 고딕을 씀
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in _FONT_CANDIDATES:
        if name in installed:
            return name
    return "sans-serif"  # 한글이 네모로 나오면 이 줄이 원인


FONT = _pick_font()
plt.rcParams["font.family"] = FONT
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지


def new_card(series, no, topic, title, how_to_read):
    """머리글(시리즈 라벨 → 제목 → 읽는 법)까지 그린 빈 카드를 돌려줍니다.
    series/no/topic 예: ("K리그2 승격 경쟁", "③", "수원삼성전 예고")
    title은 사실만(해석 금지)."""
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=SURFACE)
    fig.text(0.06, 0.90, f"{series} {no} · {topic}", fontsize=20, color=FOCUS, weight="bold")
    fig.text(0.06, 0.815, title, fontsize=40, color=TEXT_1, weight="bold")
    fig.text(0.06, 0.755, how_to_read, fontsize=21, color=TEXT_2)
    return fig


def add_footer(fig, as_of_text):
    """바닥글: 왼쪽 기준일 + 출처, 오른쪽 사이트 이름 + 주소."""
    fig.text(0.06, 0.07, as_of_text, fontsize=16, color=TEXT_3)
    fig.text(0.06, 0.035, COPYRIGHT, fontsize=16, color=TEXT_3)
    fig.text(0.94, 0.07, SITE_NAME, fontsize=18, color=TEXT_2, ha="right", weight="bold")
    fig.text(0.94, 0.035, SITE_URL, fontsize=16, color=TEXT_3, ha="right")
