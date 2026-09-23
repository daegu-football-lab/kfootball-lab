# -*- coding: utf-8 -*-
"""2편 손입력용 엑셀 파일(race_input.xlsx)을 새로 만든다.

사용법:
    python make_race_input.py

왜 엑셀인가:
    CSV는 파일 안에 "나는 UTF-8이다"라는 정보가 없다. 그래서 저장/열기마다
    인코딩 사고가 난다. .xlsx는 내부적으로 인코딩이 고정돼 있어 이 문제가 없다.

주의:
    이미 race_input.xlsx 가 있으면 덮어쓰지 않는다. (입력한 내용을 날리면 안 됨)
    새로 만들고 싶으면 기존 파일 이름을 직접 바꾼 뒤 실행할 것.
"""

import os
import sys

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    print("openpyxl 이 없습니다. 터미널에 아래를 치세요:")
    print("    pip install openpyxl")
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "raw", "race_input.xlsx")

# 색: 헤더=진한 회색, 설명줄=연한 노랑, 예시줄=연한 파랑
FILL_HEAD = PatternFill("solid", fgColor="D9D9D9")
FILL_NOTE = PatternFill("solid", fgColor="FFF2CC")
FILL_EX = PatternFill("solid", fgColor="DDEBF7")

# 시트 정의: (시트이름, [(컬럼명, 설명, 예시, 너비)], 미리채운줄, 빈줄수)
SHEETS = [
    (
        "1_팀",
        [
            ("team", "팀 이름", "대구FC", 14),
            ("rank", "순위", "4", 7),
            ("points", "승점", "46", 8),
            ("played", "치른 경기수", "26", 11),
            ("remaining", "남은 경기수", "6", 11),
            ("opp_rank_sum", "잔여 상대 순위의 합", "69", 18),
            ("recent5", "최근5경기 오래된것부터", "WDLWW", 22),
        ],
        [["대구FC", None, None, None, 6, None, None]],
        4,
    ),
    (
        "2_남은맞대결",
        [
            ("round", "라운드", "31", 9),
            ("date", "날짜 YYYY-MM-DD", "2026-10-31", 18),
            ("home_team", "홈 팀", "대구FC", 14),
            ("away_team", "원정 팀", "수원삼성", 14),
        ],
        [],
        5,
    ),
    (
        "3_대구전적",
        [
            ("date", "날짜 YYYY-MM-DD", "2026-05-18", 18),
            ("opponent", "상대 팀", "수원FC", 14),
            ("home_away", "H(홈) 또는 A(원정)", "H", 18),
            ("daegu_goals", "대구 득점", "1", 12),
            ("opp_goals", "상대 득점", "2", 12),
        ],
        [],
        6,
    ),
]

GUIDE = [
    ("2편 손입력 가이드", True),
    ("", False),
    ("[기준일 — 위 3·4행 노란 칸 두 개를 제일 먼저 채우세요]", True),
    ("", False),
    ("기준일이 뭔가요?", True),
    ("  K리그 순위표를 '언제 본 것인지' 적는 칸입니다.", False),
    ("", False),
    ("왜 필요한가", True),
    ("  - 순위와 승점은 매 라운드 바뀝니다. 오늘 4위여도 다음 주엔 3위일 수 있습니다.", False),
    ("  - 이 파일을 2주 뒤에 다시 열면, 46점이 언제 기준인지 알 방법이 없습니다.", False),
    ("  - 블로그 글에도 '9월 23일 기준' 이라고 써야 독자가 오해하지 않습니다.", False),
    ("", False),
    ("무엇을 적나", True),
    ("  기준일     = 순위표를 본 날짜. 오늘 채운다면 오늘 날짜.  예) 2026-09-23", False),
    ("  기준 라운드 = 그 시점에 몇 라운드까지 끝났는지.          예) 28", False),
    ("", False),
    ("  날짜만으로는 부족합니다. K리그2는 17팀 홀수라 매 라운드 한 팀이 쉽니다.", False),
    ("  그래서 같은 날짜에도 팀마다 치른 경기 수(played)가 다를 수 있습니다.", False),
    ("  라운드를 같이 적어야 '무엇이 끝난 시점인지'가 분명해집니다.", False),
    ("", False),
    ("제일 위험한 실수", True),
    ("  며칠에 걸쳐 나눠 입력하는 것. 그 사이 경기가 있으면 팀마다 기준이 달라집니다.", False),
    ("  한 자리에서 다 채우세요. 중간에 경기가 있었다면 처음부터 다시 확인하세요.", False),
    ("", False),
    ("-" * 90, False),
    ("", False),
    ("아래 시트 3개를 채우면 됩니다. 총 16줄.", False),
    ("", False),
    ("[규칙]", True),
    ("  1. 각 시트 2행(노란색)=칸 설명, 3행(파란색)=예시. 지우지 마세요. 코드가 무시합니다.", False),
    ("  2. 4행부터 입력하세요.", False),
    ("  3. 팀 이름 철자는 matches.csv 와 똑같아야 합니다. 예: 대구FC (띄어쓰기 없음)", False),
    ("", False),
    ("[1_팀 시트] 5줄", True),
    ("  opp_rank_sum = 남은 경기 상대들의 순위를 그냥 더한 값. 나눗셈은 하지 마세요.", False),
    ("     예) 충북청주11 + 전남16 + 수원삼성1 + 성남10 + 김해17 + 천안14 = 69", False),
    ("     숫자가 클수록 약팀이 많다 = 남은 일정이 쉽다는 뜻.", False),
    ("  recent5 = W(승) D(무) L(패) 대문자 5글자. 왼쪽이 오래된 경기입니다.", False),
    ("     축구 사이트는 보통 최신을 왼쪽에 놓으니 뒤집어 적으세요.", False),
    ("", False),
    ("[2_남은맞대결 시트] 0~5줄", True),
    ("  위 5팀끼리 아직 안 치른 경기만. 한 경기 = 한 줄.", False),
    ("  대구가 안 끼는 경기(예: 수원FC vs 서울이랜드)도 적습니다. 없으면 0줄도 정상.", False),
    ("", False),
    ("[3_대구전적 시트] 0~6줄", True),
    ("  대구FC가 위 4팀과 올 시즌 이미 치른 경기만.", False),
    ("  득점은 항상 대구 먼저. H/A 도 대구 기준입니다.", False),
    ("", False),
    ("[다 쓴 다음]", True),
    ("  저장하고 터미널에 아래 두 줄을 차례로 치세요.", False),
    ("      cd C:\dev\kfootball-lab", False),
    ("      python check_race.py", False),
    ("  빈칸/오타를 한글로 알려주고, 통과하면 CSV 파일을 자동으로 만들어 줍니다.", False),
]

# 기준일 입력 칸의 위치. check_race.py 가 이 좌표를 그대로 읽는다.
# 상수로 빼둔 이유: 안내문 줄 수가 바뀌어도 입력 칸 위치가 흔들리지 않게 하려고.
META_CELLS = [
    ("B3", "기준일 (YYYY-MM-DD)", "as_of_date"),
    ("B4", "기준 라운드 (숫자)", "as_of_round"),
]


def build_guide(ws):
    """안내 시트. A열은 설명문, B3/B4 는 실제로 입력받는 칸."""
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 70

    ws["A1"] = "2편 손입력 가이드"
    ws["A1"].font = Font(bold=True, size=14)

    # 입력 칸을 맨 위에 고정해 둔다. 스크롤해서 찾을 필요가 없게.
    ws["A3"] = "기준일"
    ws["A4"] = "기준 라운드"
    ws["C3"] = "<- 순위표를 본 날짜.  예) 2026-09-23"
    ws["C4"] = "<- 그때 몇 라운드까지 끝났는지.  예) 28"
    for addr in ("B3", "B4"):
        ws[addr].fill = FILL_NOTE
        ws[addr].font = Font(bold=True)
    for addr in ("A3", "A4"):
        ws[addr].font = Font(bold=True)
    for addr in ("C3", "C4"):
        ws[addr].font = Font(italic=True, size=9)

    for i, (text, bold) in enumerate(GUIDE[2:], start=6):
        c = ws.cell(row=i, column=1, value=text)
        c.font = Font(bold=bold)
        c.alignment = Alignment(horizontal="left")
    ws.sheet_view.showGridLines = False


def build_sheet(ws, cols, prefilled, blanks):
    # 1행: 영문 컬럼명 (코드가 이 줄을 읽는다)
    for j, (name, _desc, _ex, width) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=j, value=name)
        c.font = Font(bold=True)
        c.fill = FILL_HEAD
        ws.column_dimensions[get_column_letter(j)].width = width

    # 2행: 한글 설명. 각 칸 바로 아래에 있어야 무엇을 쓸지 눈으로 보인다.
    ws.cell(row=2, column=1, value="#" + cols[0][1])
    for j, (_name, desc, _ex, _w) in enumerate(cols[1:], start=2):
        ws.cell(row=2, column=j, value=desc)
    # 3행: 예시
    ws.cell(row=3, column=1, value="#예시 " + cols[0][2])
    for j, (_name, _desc, ex, _w) in enumerate(cols[1:], start=2):
        ws.cell(row=3, column=j, value=ex)

    for j in range(1, len(cols) + 1):
        ws.cell(row=2, column=j).fill = FILL_NOTE
        ws.cell(row=3, column=j).fill = FILL_EX
        for r in (2, 3):
            ws.cell(row=r, column=j).font = Font(italic=True, size=9)
            ws.cell(row=r, column=j).alignment = Alignment(wrap_text=True)

    # 4행부터 입력 영역
    row = 4
    for values in prefilled:
        for j, v in enumerate(values, start=1):
            ws.cell(row=row, column=j, value=v)
        row += 1
    row += blanks

    ws.freeze_panes = "A4"  # 위 3줄은 스크롤해도 항상 보이게


def main():
    force = "--force" in sys.argv
    if os.path.exists(OUT) and not force:
        print("이미 있습니다:", OUT)
        print("덮어쓰지 않았습니다. 정말 새로 만들려면:  python make_race_input.py --force")
        return 0

    wb = Workbook()
    build_guide(wb.active)
    wb.active.title = "0_안내"
    for name, cols, prefilled, blanks in SHEETS:
        build_sheet(wb.create_sheet(name), cols, prefilled, blanks)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("만들었습니다:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
