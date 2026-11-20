"""
check_site.py - 사이트를 올리기 전에 숫자와 파일을 점검합니다.

사용법 (C:\\dev\\kfootball-lab 폴더에서):
    python check_site.py

결과
  [오류]  올리면 안 되는 상태. 종료 코드 1 -> publish_site.ps1 이 멈춥니다.
  [경고]  올려도 되지만 확인이 필요한 상태. 종료 코드 0.
  [통과]  문제 없음.

왜 만들었나
  - R31 갱신분을 만들어 놓고 push 를 잊은 채 3주가 지난 일이 있었습니다(11/21 발견).
  - standings.js 를 손으로 고치거나 기준일이 서로 어긋나면, 사이트 숫자와 블로그 숫자가 달라집니다.
  - 그래서 "검사를 통과한 것만 올린다"는 규칙을 스크립트로 고정합니다.
    (참고: nfelo 같은 정적 예측 사이트도 검증을 통과한 결과만 배포합니다.)

설계 메모
  - 외부 라이브러리 없이 표준 라이브러리만 씁니다. PC 어디서나 바로 돌게 하기 위해서입니다.
  - 사이트 데이터 파일은 `window.이름 = {JSON};` 모양이라, 앞뒤를 잘라 json 으로 읽습니다.
    JS 문법이 깨졌으면 여기서 바로 걸립니다.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
DATA = SITE / "data"

# 사이트에 표시되는 기준일. src/config.py 를 import 하지 않고 글자로 읽습니다
# (config 가 pandas 등을 불러와도 이 검사는 가볍게 돌게 하려고).
CONFIG = ROOT / "src" / "config.py"

FIXTURES_STALE_DAYS = 14  # 일정표를 이 기간보다 오래 확인 안 했으면 경고


class Report:
    """오류/경고를 모아 두었다가 마지막에 한 번에 보여 줍니다."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self, msg: str) -> None:
        self.passed.append(msg)

    def print(self) -> int:
        for m in self.passed:
            print(f"[통과] {m}")
        for m in self.warnings:
            print(f"[경고] {m}")
        for m in self.errors:
            print(f"[오류] {m}")
        print("-" * 50)
        print(f"오류 {len(self.errors)} / 경고 {len(self.warnings)} / 통과 {len(self.passed)}")
        return 1 if self.errors else 0


# ---------------------------------------------------------------- 읽기 도구
class NoNode(Exception):
    """JSON 이 아닌 JS 파일인데 node 가 없어 검사를 못 한 경우."""


def load_site_js(path: Path) -> dict:
    """`window.KFL_X = {...};` 파일을 dict 로 읽습니다.

    1차: JSON 으로 읽기 (run.py 가 만든 파일은 전부 JSON 모양)
    2차: 사람이 직접 고치는 파일(series.js 등)은 JS 객체 문법이라 node 로 실제 실행해 봄
    실패하면 ValueError, node 가 없으면 NoNode.
    """
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.\w+\s*=\s*", text)
    if not m:
        raise ValueError("`window.이름 = ` 줄이 없습니다")
    body = text[m.end():].strip()
    if body.endswith(";"):
        body = body[:-1]
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass
    script = ("global.window={};require(process.argv[1]);"
              "const v=Object.values(window);process.stdout.write(JSON.stringify(v[v.length-1]))")
    try:
        r = subprocess.run(["node", "-e", script, str(path)], capture_output=True,
                           text=True, encoding="utf-8")
    except OSError as e:
        raise NoNode from e
    if r.returncode != 0:
        lines = [x for x in r.stderr.splitlines() if "Error" in x]
        raise ValueError(lines[0] if lines else "JS 실행 실패")
    return json.loads(r.stdout)


def read_config_value(name: str) -> str | None:
    m = re.search(rf'^{name}\s*=\s*"([^"]*)"', CONFIG.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def git(*args: str) -> list[str]:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return ["__git_failed__"]
    return [line for line in out.splitlines() if line.strip()]


# ---------------------------------------------------------------- 검사 항목
def check_js_files(rep: Report) -> dict[str, dict]:
    """1) 데이터 파일이 전부 읽히는가."""
    loaded = {}
    for path in sorted(DATA.glob("*.js")):
        try:
            loaded[path.stem] = load_site_js(path)
        except NoNode:
            rep.warn(f"{path.name}: JSON 모양이 아니고 node 도 없어 문법 검사를 건너뜀")
        except (ValueError, json.JSONDecodeError) as e:
            rep.error(f"{path.name} 읽기 실패: {e}")
    if loaded:
        rep.ok(f"데이터 파일 {len(loaded)}개 문법 정상")
    return loaded


def check_dates(rep: Report, d: dict[str, dict]) -> None:
    """2) 기준일이 서로 맞는가."""
    as_of = read_config_value("DATA_AS_OF")
    note = read_config_value("DATA_AS_OF_NOTE")
    st = d.get("standings", {}).get("meta", {})
    if st.get("as_of") != as_of or st.get("as_of_note") != note:
        rep.error(f"standings.js 기준일({st.get('as_of')}, {st.get('as_of_note')}) ≠ "
                  f"config.py({as_of}, {note}) → python run.py standings 다시 실행")
    else:
        rep.ok(f"기준일 일치: {as_of} ({note})")

    rc = d.get("recent", {})
    if rc.get("matches"):
        last = rc["matches"][-1]["date"]
        if as_of and last > as_of:
            rep.error(f"recent.js 마지막 경기({last})가 기준일({as_of})보다 뒤입니다")
        # 기준일 전에 끝난 대구 경기가 recent 에 빠졌는지 (일정표 기준)
        team = d.get("standings", {}).get("meta", {}).get("team", "대구FC")
        played = [f for f in d.get("fixtures", {}).get("fixtures", [])
                  if team in (f.get("home"), f.get("away")) and last < f["date"] <= (as_of or "")]
        for f in played:
            rep.warn(f"R{f['round']} {f['date']} {f['home']}-{f['away']} 가 기준일 전 경기인데 "
                     f"recent.js 에 없습니다 → raw_pages.txt 추가 후 run.py recent")

    fx = d.get("fixtures", {}).get("meta", {})
    checked = fx.get("checked_at")
    if checked and as_of:
        gap = (dt.date.fromisoformat(as_of) - dt.date.fromisoformat(checked)).days
        if gap > FIXTURES_STALE_DAYS:
            rep.warn(f"fixtures.js 일정 확인일({checked})이 기준일보다 {gap}일 오래됐습니다")


def check_standings_math(rep: Report, d: dict[str, dict]) -> None:
    """3) 순위표 산수: 3승+무=승점, 승+무+패=경기수, 경기수 합은 짝수."""
    teams = d.get("standings", {}).get("teams", [])
    bad = [t["team"] for t in teams
           if 3 * t["승"] + t["무"] != t["승점"] or t["승"] + t["무"] + t["패"] != t["경기수"]]
    total = sum(t["경기수"] for t in teams)
    if bad:
        rep.error(f"승점/경기수 계산이 안 맞는 팀: {', '.join(bad)}")
    if total % 2:
        rep.error(f"전체 경기수 합 {total} 이 홀수입니다 (한 경기는 두 팀이 같이 치름)")
    if teams and not bad and total % 2 == 0:
        rep.ok(f"순위표 산수 정상 ({len(teams)}팀, {total // 2}경기)")

    for m in d.get("recent", {}).get("matches", []):
        expect = "승" if m["gf"] > m["ga"] else "무" if m["gf"] == m["ga"] else "패"
        if m["result"] != expect:
            rep.error(f"recent.js {m['date']} 결과 표기 {m['result']} ≠ 스코어 {m['gf']}-{m['ga']}")


def check_assets(rep: Report) -> None:
    """4) index.html 이 부르는 파일이 실제로 있는가."""
    html = (SITE / "index.html").read_text(encoding="utf-8")
    refs = set(re.findall(r'(?:src|href)="([^"#:?]+\.(?:js|css|svg|png))"', html))
    # 백과 그림 경로(img: { src: "img/..." })는 화면 코드(js/app.js)에 있습니다. 경로는 site/ 기준.
    code = html + "".join(p.read_text(encoding="utf-8") for p in (SITE / "js").glob("*.js"))
    refs |= set(re.findall(r'src:\s*"([^"]+\.(?:svg|png))"', code))
    missing = [r for r in sorted(refs) if not (SITE / r).exists()]
    if missing:
        rep.error("index.html 이 부르는데 없는 파일: " + ", ".join(missing))
    else:
        rep.ok(f"index.html 이 부르는 파일 {len(refs)}개 모두 있음")


def check_git(rep: Report) -> None:
    """5) 원시 데이터가 git 에 없는가 / 올리지 않은 변경이 남았는가."""
    tracked = git("ls-files")
    if tracked == ["__git_failed__"]:
        rep.warn("git 을 실행하지 못해 커밋 상태는 검사하지 않았습니다")
        return
    leaked = [f for f in tracked if f.startswith("data/raw/") or f.endswith(".csv")]
    if leaked:
        rep.error("원시 데이터가 git 에 올라가 있습니다(약관 제4조): " + ", ".join(leaked[:5]))
    else:
        rep.ok("git 에 원시 데이터(CSV) 없음")

    status = git("status", "--porcelain", "--", "site", "index.html", "src/config.py")
    pending = [s[3:] for s in status if not s[3:].endswith(".bak") and ".bak_" not in s]
    if pending:
        rep.warn("아직 올리지 않은 사이트 파일 " + str(len(pending)) + "개: " + ", ".join(pending))

    ahead = git("rev-list", "--count", "@{u}..HEAD")
    if ahead and ahead[0].isdigit() and int(ahead[0]) > 0:
        rep.warn(f"커밋은 했지만 push 안 된 커밋 {ahead[0]}개 → git push")


def main() -> int:
    rep = Report()
    loaded = check_js_files(rep)
    check_dates(rep, loaded)
    check_standings_math(rep, loaded)
    check_assets(rep)
    check_git(rep)
    return rep.print()


if __name__ == "__main__":
    sys.exit(main())
