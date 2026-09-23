# -*- coding: utf-8 -*-
"""2편 손입력 검사 + CSV 변환.

사용법:
    python check_race.py

하는 일:
    1) data/raw 안 CSV들의 인코딩을 검사한다 (엑셀에서 한글이 깨지는 원인)
    2) race_input.xlsx 세 시트의 입력값을 검사한다
    3) 문제가 없으면 분석 코드가 읽을 CSV 3개를 자동으로 만든다

설계 메모:
    - 사람이 채우는 파일은 .xlsx 하나. 엑셀은 인코딩 정보를 파일 안에 갖고 있어서
      CP949/UTF-8 사고가 구조적으로 안 난다.
    - 분석 코드가 읽는 형식은 CSV 그대로 둔다. 기존 코드를 안 건드리기 위해서다.
      즉 이 스크립트는 "입력 게이트": 검사 + 표준 형식으로 변환.
    - 생성된 CSV는 손으로 고치지 않는다. 고치면 다음 실행 때 덮어써진다.
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw")
XLSX = os.path.join(RAW, "race_input.xlsx")

NG = "  [고쳐야 함]"
GEN_MARK = "#자동 생성 파일입니다. 고치려면 race_input.xlsx 를 고치고 check_race.py 를 다시 실행하세요."

SHEETS = {
    "1_팀": ("race_teams.csv",
             ["team", "rank", "points", "played", "remaining",
              "opp_rank_sum", "recent5"]),
    "2_남은맞대결": ("race_h2h_remaining.csv",
                ["round", "date", "home_team", "away_team"]),
    "3_대구전적": ("race_h2h_past.csv",
               ["date", "opponent", "home_away", "daegu_goals", "opp_goals"]),
}


# ---------------------------------------------------------------- 인코딩 검사

def diagnose_encoding(path):
    """CSV 한 개의 인코딩 상태를 (상태, 설명)으로 돌려준다.

    파일 안에는 인코딩 정보가 원래 없다. 그래서 바이트를 보고 추측한다.
      - 맨 앞 EF BB BF (BOM)  -> UTF-8 임을 엑셀이 알 수 있음. 정상
      - BOM 없이 UTF-8        -> 파이썬은 OK, 엑셀에서 한글 깨짐
      - UTF-8로 못 읽힘       -> CP949 로 저장된 것. 파이썬에서 깨짐
    """
    with open(path, "rb") as f:
        head = f.read(3)
        f.seek(0)
        data = f.read()

    if head == b"\xef\xbb\xbf":
        return "ok", "UTF-8 (BOM 있음)"

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            data.decode("cp949")
            return "bad", ("CP949로 저장됨. 엑셀에서 열어 "
                           "'CSV UTF-8(쉼표로 분리)'로 다시 저장하세요")
        except UnicodeDecodeError:
            return "bad", "알 수 없는 인코딩"

    if all(ord(ch) < 128 for ch in text):
        return "ok", "영어/숫자만 있음 (인코딩 문제 없음)"
    return "warn", "UTF-8이지만 BOM 없음. 엑셀로 열면 한글이 깨져 보입니다"


def check_encodings(problems):
    print("\n[1/5] data/raw CSV 인코딩")
    names = sorted(n for n in os.listdir(RAW) if n.lower().endswith(".csv"))
    if not names:
        print("      CSV 없음")
        return
    for name in names:
        state, msg = diagnose_encoding(os.path.join(RAW, name))
        mark = {"ok": "  OK  ", "warn": "  주의 ", "bad": "  오류 "}[state]
        print("%s %-26s %s" % (mark, name, msg))
        if state == "bad":
            problems.append("%s: %s" % (name, msg))


# ---------------------------------------------------------------- 기준일

def check_meta(problems, wb):
    """0_안내 시트의 B3(기준일) / B4(기준 라운드)를 검사한다.

    왜 강제하나:
        순위·승점은 매 라운드 바뀐다. 기준 시점이 없으면 이 숫자들은
        나중에 해석할 수 없는 숫자가 된다. 블로그 글에도 명시해야 한다.
    """
    print("\n[2/5] 기준일 (0_안내 시트 B3 / B4)")
    if "0_안내" not in wb.sheetnames:
        problems.append("엑셀에 '0_안내' 시트가 없습니다")
        print(NG, "시트가 없습니다")
        return None

    ws = wb["0_안내"]
    raw_date = ws["B3"].value
    raw_round = ws["B4"].value

    date_text = ""
    if raw_date is None or str(raw_date).strip() == "":
        problems.append("기준일(0_안내 B3)이 비었습니다. 순위표를 본 날짜를 적으세요")
    else:
        # 엑셀에서 날짜로 입력하면 datetime 으로, 글자로 입력하면 문자열로 온다
        if hasattr(raw_date, "strftime"):
            date_text = raw_date.strftime("%Y-%m-%d")
        else:
            date_text = str(raw_date).strip()
        parts = date_text.split("-")
        ok = (len(parts) == 3 and len(parts[0]) == 4
              and all(p.isdigit() for p in parts))
        if not ok:
            problems.append("기준일(B3)은 YYYY-MM-DD 형식이어야 합니다. 예: 2026-09-23")
            date_text = ""

    round_text = ""
    if raw_round is None or str(raw_round).strip() == "":
        problems.append("기준 라운드(0_안내 B4)가 비었습니다. 몇 라운드까지 끝났는지 적으세요")
    elif not is_int(raw_round):
        problems.append("기준 라운드(B4)는 숫자여야 합니다. 예: 28")
    else:
        round_text = str(int(float(str(raw_round).strip())))

    if date_text and round_text:
        print("      %s / %s라운드 종료 시점" % (date_text, round_text))
    return {"as_of_date": date_text, "as_of_round": round_text}


# ---------------------------------------------------------------- 엑셀 읽기

def load_sheets():
    """race_input.xlsx 를 읽어 {시트이름: [dict, ...]} 로 돌려준다."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        print("\nopenpyxl 이 없습니다. 터미널에 아래를 치세요:")
        print("    pip install openpyxl")
        sys.exit(1)

    if not os.path.exists(XLSX):
        print("\n" + XLSX + " 가 없습니다.")
        print("먼저 아래를 치세요:  python make_race_input.py")
        sys.exit(1)

    wb = load_workbook(XLSX, data_only=True)
    out = {}
    for sheet, (_csvname, cols) in SHEETS.items():
        if sheet not in wb.sheetnames:
            out[sheet] = None
            continue
        ws = wb[sheet]
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            first = "" if row[0] is None else str(row[0]).strip()
            if first.startswith("#"):          # 설명줄/예시줄은 건너뛴다
                continue
            cells = [("" if v is None else str(v).strip()) for v in row[:len(cols)]]
            if not any(cells):                  # 아직 안 쓴 줄
                continue
            rows.append(dict(zip(cols, cells)))
        out[sheet] = rows
    return out, wb


def is_int(value):
    try:
        int(float(str(value).strip()))
        return True
    except (ValueError, TypeError):
        return False


def known_teams():
    """matches.csv 에 실제로 나오는 팀 이름. 철자 검증에 쓴다."""
    path = os.path.join(RAW, "matches.csv")
    if not os.path.exists(path):
        return set()
    teams = set()
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            teams.add((row.get("home_team") or "").strip())
            teams.add((row.get("away_team") or "").strip())
    teams.discard("")
    return teams


# ---------------------------------------------------------------- 내용 검사

def check_teams(problems, warnings, rows):
    print("\n[3/5] 1_팀 시트")
    if rows is None:
        problems.append("엑셀에 '1_팀' 시트가 없습니다")
        print(NG, "시트가 없습니다")
        return []

    print("      입력된 줄: %d개 (5개가 목표)" % len(rows))
    if len(rows) < 5:
        print(NG, "아직 %d줄 더 남았습니다" % (5 - len(rows)))

    valid = known_teams()
    names = []
    for i, r in enumerate(rows, start=1):
        team = r.get("team", "")
        label = "1_팀 %d번째 줄(%s)" % (i, team or "팀 이름 비었음")
        if not team:
            problems.append(label + ": 팀 이름이 비었습니다")
            continue
        names.append(team)
        if valid and team not in valid:
            warnings.append(label + ": matches.csv에 없는 이름입니다. "
                            "오타인지 확인하세요 (샘플 데이터라면 정상)")
        for col in ("rank", "points", "played", "remaining", "opp_rank_sum"):
            if not is_int(r.get(col)):
                problems.append(label + ": %s 칸이 비었거나 숫자가 아닙니다" % col)
        form = r.get("recent5", "").upper()
        if len(form) != 5 or any(ch not in "WDL" for ch in form):
            problems.append(label + ": recent5는 W/D/L 대문자 5글자 (예: WDLWW)")

    if "대구FC" not in names:
        problems.append("1_팀 시트에 대구FC가 없습니다")
    return names


def check_remaining(problems, rows, names):
    print("\n[4/5] 2_남은맞대결 시트")
    if rows is None:
        problems.append("엑셀에 '2_남은맞대결' 시트가 없습니다")
        print(NG, "시트가 없습니다")
        return
    print("      입력된 줄: %d개 (0개여도 정상입니다)" % len(rows))
    for i, r in enumerate(rows, start=1):
        label = "맞대결 %d번째 줄" % i
        if not is_int(r.get("round")):
            problems.append(label + ": round가 숫자가 아닙니다")
        for col in ("home_team", "away_team"):
            team = r.get(col, "")
            if names and team not in names:
                problems.append("%s: %s '%s' 가 1_팀 시트에 없는 팀입니다"
                                % (label, col, team))


def check_past(problems, rows, names):
    print("\n[5/5] 3_대구전적 시트")
    if rows is None:
        problems.append("엑셀에 '3_대구전적' 시트가 없습니다")
        print(NG, "시트가 없습니다")
        return
    print("      입력된 줄: %d개" % len(rows))
    for i, r in enumerate(rows, start=1):
        label = "전적 %d번째 줄" % i
        opp = r.get("opponent", "")
        if names and opp and opp not in names:
            problems.append("%s: 상대 '%s' 가 1_팀 시트에 없는 팀입니다" % (label, opp))
        if r.get("home_away", "").upper() not in ("H", "A"):
            problems.append(label + ": home_away는 H 또는 A 여야 합니다")
        for col in ("daegu_goals", "opp_goals"):
            if not is_int(r.get(col)):
                problems.append(label + ": %s 가 숫자가 아닙니다" % col)


# ---------------------------------------------------------------- CSV 내보내기

def export_csv(data, meta):
    """검사를 통과했을 때만 호출. 분석 코드가 읽을 CSV를 만든다."""
    made = []
    for sheet, (csvname, cols) in SHEETS.items():
        rows = data.get(sheet) or []
        path = os.path.join(RAW, csvname)
        # newline="" 은 윈도우에서 빈 줄이 끼는 것을 막는 표준 방법
        # utf-8-sig 는 BOM을 붙여 엑셀에서도 안 깨지게 한다
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(GEN_MARK + "\n")
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        made.append("%s (%d줄)" % (csvname, len(rows)))

    # 기준 시점은 별도 파일로. 분석·차트·블로그 글에서 모두 이 값을 인용한다.
    meta_path = os.path.join(RAW, "race_meta.csv")
    with open(meta_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(GEN_MARK + "\n")
        w = csv.writer(f)
        w.writerow(["as_of_date", "as_of_round"])
        w.writerow([meta["as_of_date"], meta["as_of_round"]])
    made.append("race_meta.csv (기준일 %s, %s라운드)"
                % (meta["as_of_date"], meta["as_of_round"]))
    return made


def main():
    print("=" * 56)
    print(" 2편 손입력 검사")
    print("=" * 56)

    problems = []   # 있으면 CSV를 안 만든다 (치명적)
    warnings = []   # 알려만 주고 진행한다 (사람이 판단할 일)
    check_encodings(problems)
    data, wb = load_sheets()
    meta = check_meta(problems, wb)
    names = check_teams(problems, warnings, data.get("1_팀"))
    check_remaining(problems, data.get("2_남은맞대결"), names)
    check_past(problems, data.get("3_대구전적"), names)

    print("\n" + "=" * 56)
    if warnings:
        print(" 확인해 보세요 %d개 (진행은 됩니다)" % len(warnings))
        for w in warnings:
            print(" ?", w)
        print("=" * 56)
    if problems:
        print(" 고쳐야 할 것 %d개" % len(problems))
        print("=" * 56)
        for p in problems:
            print(" -", p)
        print("\n CSV는 만들지 않았습니다. 위를 고치고 다시 실행하세요.")
        return 1

    print(" 통과. CSV를 만들었습니다.")
    print("=" * 56)
    for line in export_csv(data, meta):
        print(" -", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
