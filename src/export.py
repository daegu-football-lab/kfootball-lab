"""
4단계: 내보내기

두 가지를 만듭니다.
  1) site/data/players.json  -> 웹사이트가 읽는 데이터
  2) posts/YYYY-MM-DD_*.md   -> 블로그 글 '초안' (해석은 직접 쓰세요)

원칙: 숫자와 차트는 자동, 해석과 의견은 사람이 직접.
      자동으로 만든 문장을 그대로 올리면 글의 신뢰도가 떨어집니다.
      구단이 보는 건 '이 사람이 숫자를 어떻게 읽는가'이기 때문입니다.
"""

import json
from datetime import date

from . import analyze, config


def export_site_json(data: dict) -> str:
    """웹사이트용 JSON 한 개로 묶어서 저장"""
    per90 = analyze.player_per90(data)
    team_table = analyze.team_season_table(data)
    matches = data["matches"]

    # 우리 팀 선수 전원에 대해 On/Off를 미리 계산해 둡니다
    # (사이트는 정적 파일이라 클릭할 때마다 계산할 수 없으므로 미리 만들어 둠)
    onoff = {}
    for player in per90["player"]:
        r = analyze.on_off_analysis(data, player)
        if r["on"] and r["off"]:
            onoff[player] = r

    payload = {
        "meta": {
            "team": config.MY_TEAM,
            "season": config.SEASON,
            "generated_at": date.today().isoformat(),
            # 선수·경기 데이터가 아직 샘플인지 (실제 입력을 마치면 False 로 바꾸세요)
            "is_sample": True,
            # 팀 시즌 누적(team_season_stats.csv)이 채워져 있으면 팀 비교는 실제 데이터
            "team_is_real": data.get("team_season") is not None,
        },
        "players": per90.to_dict(orient="records"),
        "teams": team_table.to_dict(orient="records"),
        "matches": matches.to_dict(orient="records"),
        "onoff": onoff,
    }

    path = config.SITE_DATA_DIR / "players.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  사이트 데이터 저장: site/data/{path.name}")

    # 같은 내용을 .js 파일로도 저장합니다.
    #
    # 왜 두 번 저장하나요? (실무에서 자주 걸리는 함정)
    #   index.html을 그냥 더블클릭해서 열면 주소가 file:// 로 시작합니다.
    #   이때 브라우저 보안 정책(CORS) 때문에 fetch()로 json을 못 읽습니다.
    #   .js 파일은 <script> 태그로 불러오므로 이 제한을 받지 않습니다.
    #   => 로컬에서는 .js, 나중에 GitHub Pages에 올리면 둘 다 동작합니다.
    js_path = config.SITE_DATA_DIR / "players.js"
    js_path.write_text(
        "window.KFL_DATA = " + json.dumps(payload, ensure_ascii=False) + ";",
        encoding="utf-8",
    )
    print(f"  사이트 데이터 저장: site/data/{js_path.name}")
    return str(path)


def export_post_draft(result: dict, chart_paths: list[str]) -> str:
    """On/Off 분석 결과로 블로그 글 초안 생성"""
    player = result["player"]
    on, off, diff = result["on"], result["off"], result["diff"]

    lines = [
        f"# {player}, 있을 때와 없을 때 {config.MY_TEAM}는 어떻게 달라졌나",
        "",
        "> 이 글은 초안입니다. 아래 `[직접 작성]` 부분을 채운 뒤 발행하세요.",
        "",
        "## 왜 이걸 봤나",
        "",
        "[직접 작성] 이 선수를 고른 이유를 2~3문장으로.",
        "",
        "## 숫자로 본 차이",
        "",
        f"| 지표 | 출전 {on['경기수']}경기 | 결장 {off['경기수']}경기 | 차이 |",
        "|---|---:|---:|---:|",
    ]

    for key in on:
        if key == "경기수":
            continue
        d = diff[key]
        sign = "+" if d > 0 else ""
        lines.append(f"| {key} | {on[key]} | {off[key]} | {sign}{d} |")

    lines += [
        "",
        "## 이 숫자를 어떻게 읽어야 하나",
        "",
        "[직접 작성] 가장 눈에 띄는 차이 하나를 골라 설명하세요.",
        "[직접 작성] 경기 장면을 떠올리며 '왜 그런 숫자가 나왔는지' 해석을 붙이세요.",
        "",
        "## 주의해서 봐야 할 점",
        "",
    ]

    if result.get("warning"):
        lines.append(f"- {result['warning']}")
    lines += [
        "- 상대 팀 전력과 홈/원정이 섞여 있어, 이 차이가 전부 선수 한 명 때문이라고 말할 수는 없습니다.",
        "- '상대 패스 성공률'은 압박의 간접 지표입니다. 정식 지표(PPDA)는 좌표 데이터가 있어야 계산됩니다.",
        "",
        "## 차트",
        "",
    ]
    for p in chart_paths:
        name = p.replace("\\", "/").split("/")[-1]
        lines.append(f"![{name}](../output/charts/{name})")
    lines += [
        "",
        "---",
        "",
        f"- 데이터: [직접 작성 — 출처와 수집일을 반드시 표기]",
        f"- 분석 코드: [직접 작성 — GitHub 저장소 링크]",
        f"- 작성일: {date.today().isoformat()}",
        "",
    ]

    filename = f"{date.today().isoformat()}_{player}_onoff.md"
    path = config.POST_DIR / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  글 초안 저장: posts/{filename}")
    return str(path)


def export_standings_post(table, reg: dict, race: dict, chart_path: str) -> str:
    """
    연재 1편 "승격 경쟁팀, 숫자로 줄 세워보기" 초안 생성.

    원칙: 표와 숫자는 자동, 해석 문장은 전부 (빈칸).
          자동으로 만든 해석을 그대로 발행하면 포트폴리오 가치가 사라집니다.
    """
    from . import standings

    team = race["team"]
    rtab = reg["table"]
    sig = rtab[rtab["유의"]]

    L = [
        "# 승격 경쟁팀, 숫자로 줄 세워보기",
        "",
        "> 초안입니다. `(빈칸)` 을 직접 채운 뒤 발행하세요.",
        "",
        "## 1. 왜 순위표만으로는 부족한가",
        "",
        f"- K리그2 2026은 17팀 2로빈, 팀당 {standings.TOTAL_MATCHES_PER_TEAM}경기입니다.",
        f"- 현재 소화 경기 수가 {int(table['matches'].min())}~{int(table['matches'].max())}경기로 "
        "섞여 있습니다. 총 승점을 그대로 비교하면 착시가 생깁니다.",
        "- 승격 방식: 1~2위 자동 승격, 3~6위 승격 플레이오프.",
        "",
        "(빈칸) 이 글에서 답하려는 질문을 한 문장으로.",
        "",
        "## 2. 1차 보정: 경기당 승점(PPG)",
        "",
        "| 순위(PPG) | 팀 | 경기 | 승점 | PPG | 득실차 | 총점순위 | 변동 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in table.iterrows():
        mv = int(r["순위변동"])
        mv_s = "-" if mv == 0 else f"{'▲' if mv > 0 else '▼'}{abs(mv)}"
        L.append(
            f"| {int(r['PPG순위'])} | {r['team']} | {int(r['matches'])} | "
            f"{int(r['points'])} | {r['경기당승점']:.3f} | {int(r['득실차']):+d} | "
            f"{int(r['총점순위'])} | {mv_s} |"
        )

    changed = table[table["순위변동"] != 0]["team"].tolist()
    L += [
        "",
        f"- PPG 보정으로 순위가 바뀐 팀: {', '.join(changed) if changed else '없음'}",
        "",
        "(빈칸) 순위가 바뀐 팀이 있는가? 없다면 그것도 결과다 — 어떻게 읽을 것인가.",
        "",
        "## 3. 내용과 결과: 경기당 득실차 대비 PPG",
        "",
        f"![회귀 산점도](../output/charts/{chart_path.replace(chr(92), '/').split('/')[-1]})",
        "",
        f"- 회귀식: `PPG = {reg['intercept']} + {reg['slope']} × 경기당 득실차`",
        f"- **R² = {reg['r2']}** — 득실차가 승점 변동의 "
        f"{reg['r2'] * 100:.0f}%를 설명합니다.",
        f"- 잔차 표준편차(σ) = {reg['resid_sd']} PPG. "
        f"1.5σ 미만은 표본 17개에서 노이즈와 구분되지 않습니다.",
        "",
        "| 팀 | 잔차(PPG) | σ | 지금까지 더/덜 번 승점 | 판정 |",
        "|---|---:|---:|---:|---|",
    ]
    for _, r in rtab.iterrows():
        verdict = "유의미" if r["유의"] else "노이즈"
        L.append(
            f"| {r['team']} | {r['잔차']:+.3f} | {r['시그마']:+.2f} | "
            f"{r['잔차_시즌환산']:+.1f}점 | {verdict} |"
        )

    L += [
        "",
        f"- 1.5σ 이상 벗어난 팀: "
        f"{', '.join(sig['team']) if len(sig) else '없음'}",
        "",
        "(빈칸) 추세선에서 벗어난 팀 중 눈에 띄는 곳은? 단, 그 이유는 이 데이터로 알 수 없다.",
        f"(빈칸) {team}의 위치를 어떻게 읽을 것인가 — 단정하지 말고 가설로.",
        "",
        "## 4. 자동 승격(2위) 추격 시나리오",
        "",
        f"- {team}: 현재 {race['현재승점']}점, 잔여 {race['잔여경기']}경기, "
        f"산술적 최대 {race['최대가능승점']}점",
        f"- 현재 페이스(PPG)가 유지될 경우 최종 승점 추정: "
        + ", ".join(f"{k} {v}점" for k, v in race["현재페이스_최종승점"].items()),
        "",
        "> 이것은 **확률이 아니라 산술**입니다. "
        "경쟁팀이 남은 경기에서 몇 점을 따느냐를 독자가 직접 골라서 읽는 표입니다.",
        "",
    ]
    sc = race["시나리오표"]
    if len(sc):
        L.append("| " + " | ".join(sc.columns) + " |")
        L.append("|" + "---|" * len(sc.columns))
        for _, r in sc.iterrows():
            L.append("| " + " | ".join(str(v) for v in r.tolist()) + " |")

    L += [
        "",
        "",
        f"※ 이 표는 2위 팀({race['핵심경쟁팀']})만 상대로 계산한 것입니다. "
        "3위 이하 팀도 같은 자리를 노리고 있으므로, 이 표를 통과해도 2위가 보장되지는 않습니다.",
        "",
        "(빈칸) 이 표에서 현실적인 줄은 어디인가? 그 근거는?",
        "",
        "## 5. 이 숫자로 말할 수 없는 것",
        "",
        "- **일정 난이도(SOS) 미보정**: 상위권 팀을 이미 다 만난 팀과 아직 안 만난 팀이 섞여 있습니다.",
        "- **표본 17개**: 회귀선의 신뢰구간이 넓습니다. 1.5σ 미만 잔차는 해석하지 않았습니다.",
        f"- **대패 왜곡**: 한 경기 대패가 득실차를 크게 흔듭니다. "
        f"{race.get('왜곡사례', '')}이(가) 그 사례입니다 — "
        f"득실차는 바닥권인데 잔차는 상위권입니다. 차트에서 회색으로 표시했습니다.",
        "- **인과 아님**: 잔차가 크다고 해서 '승부처에 강하다'고 말할 수 없습니다. "
        "박빙 경기 결과의 분포일 수도 있습니다.",
        "- **스냅샷**: 아래 수집일 기준입니다. 발행 시점과 어긋날 수 있습니다.",
        "- **홈/원정 미분리**",
        "",
        "(빈칸) 다음 편 예고 — 팀 단위 숫자가 설명하지 못한 것은 무엇인가.",
        "",
        "---",
        "",
        "본 분석에 사용된 데이터의 저작권 및 소유권은 한국프로축구연맹(K LEAGUE)에 있습니다.",
        "",
        "- 데이터 수집일: (빈칸 — 옮겨 적은 날짜를 반드시 표기)",
        "- 분석 코드: (빈칸 — GitHub 저장소 링크)",
        f"- 작성일: {date.today().isoformat()}",
        "",
    ]

    filename = f"{date.today().isoformat()}_승격경쟁_줄세우기.md"
    path = config.POST_DIR / filename

    # 덮어쓰기 방지 (중요)
    #   초안에 해석을 써넣은 뒤 코드를 다시 돌리면 글이 통째로 날아갑니다.
    #   같은 이름의 파일이 이미 있으면 _v2, _v3 ... 로 새로 만듭니다.
    #   실무에서 '사람이 손댄 파일은 자동 생성기가 건드리지 않는다'는 것은 기본 원칙입니다.
    if path.exists():
        n = 2
        while (config.POST_DIR / f"{path.stem}_v{n}.md").exists():
            n += 1
        path = config.POST_DIR / f"{path.stem}_v{n}.md"
        print(f"  [주의] 기존 초안이 있어 덮어쓰지 않았습니다.")
        print(f"         새 파일로 저장합니다: posts/{path.name}")

    path.write_text("\n".join(L), encoding="utf-8")
    print(f"  글 초안 저장: posts/{path.name}")
    return str(path)


def export_standings_json(table, reg: dict, race: dict) -> str:
    """
    순위표 분석 결과를 사이트가 읽을 수 있는 형태로 내보냅니다.

    왜 players.js 와 파일을 나누나요?
      players.js 는 '대구 경기 기록'에서 나온 것이고,
      이것은 '리그 17팀 순위표'에서 나온 것입니다.
      출처가 다른 데이터를 한 파일에 섞으면, 나중에 어느 숫자가
      어디서 왔는지 추적이 안 됩니다. 실무에서 제일 흔한 사고입니다.

    공개해도 되는가?
      여기 담기는 것은 순위·승점·득실차 같은 '집계값'과 그것을 가공한
      회귀 결과입니다. 경기별 원시 기록이 아니므로 공개해도 됩니다.
    """
    rt = reg["table"]
    order = {t: i for i, t in enumerate(table["team"])}   # 리그 순위 순서 유지

    teams = []
    for _, r in rt.iterrows():
        base = table[table["team"] == r["team"]].iloc[0]
        teams.append({
            "team": r["team"],
            "경기수": int(base["matches"]),
            "승점": int(base["points"]),
            "PPG": round(float(base["경기당승점"]), 3),
            "득실차": int(base["득실차"]),
            "경기당득실차": round(float(base["경기당득실차"]), 3),
            "총점순위": int(base["총점순위"]),
            "PPG순위": int(base["PPG순위"]),
            "순위변동": int(base["순위변동"]),
            "잔차": round(float(r["잔차"]), 3),
            "시그마": round(float(r["시그마"]), 2),
            "잔차_시즌환산": round(float(r["잔차_시즌환산"]), 1),
            "유의": bool(r["유의"]),
        })
    teams.sort(key=lambda t: order[t["team"]])

    sc = race["시나리오표"]
    payload = {
        "meta": {
            "team": config.MY_TEAM,
            "season": config.SEASON,
            "generated_at": date.today().isoformat(),
            "출처": "한국프로축구연맹(K LEAGUE) 공식 기록",
        },
        "teams": teams,
        "reg": {
            "slope": reg["slope"], "intercept": reg["intercept"],
            "r2": reg["r2"], "resid_sd": reg["resid_sd"],
        },
        "race": {
            "team": race["team"],
            "현재승점": race["현재승점"],
            "잔여경기": race["잔여경기"],
            "최대가능승점": race["최대가능승점"],
            "핵심경쟁팀": race["핵심경쟁팀"],
            "시나리오": sc.to_dict(orient="records") if len(sc) else [],
            "페이스": race["현재페이스_최종승점"],
            "왜곡사례": race.get("왜곡사례"),
        },
    }

    path = config.SITE_DATA_DIR / "standings.js"
    path.write_text(
        "window.KFL_STANDINGS = " + json.dumps(payload, ensure_ascii=False) + ";",
        encoding="utf-8")
    print(f"  사이트 데이터 저장: site/data/{path.name}")
    return str(path)
