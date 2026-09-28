# CLAUDE.md

This file provides guidance to Claude Code (and, via GEMINI.md, Gemini CLI) when working in this repository.

## What this is

**개인 프로젝트**: K리그2 대구FC 데이터를 분석해서 블로그 글과 정적 분석 웹사이트("대구 풋볼 랩")를 만드는 파이프라인. 취미 이상의 목적이 있음 — README의 로드맵(2026 Q4~2027 Q3)에 적혀 있듯, 축구 데이터 분석 포트폴리오를 쌓아서 구단 전력분석관/축구산업 쪽에 지원하는 게 최종 목표. 작업을 도울 때 "이게 결국 포트폴리오/구직에 도움이 되는가"를 염두에 둘 것.

한 번 실행하면 세 가지가 한꺼번에 나옴: `데이터(CSV) → 분석 → ① 차트 PNG ② 웹사이트 데이터 ③ 블로그 글 초안`

## 폴더 구조

```
run.py                  ← 이것만 실행하면 전부 돌아감 (python run.py [선수이름])
data/raw/                실제 데이터 CSV (matches, lineups, team/player_match_stats, team_season_stats 등)
src/
  config.py              팀 이름/색상/경로 설정
  load.py                데이터 읽기 (나중에 K리그 API로 바꿀 지점)
  analyze.py             On/Off 분석, 팀 비교, 90분당 지표
  charts.py              차트 PNG 생성
  export.py              사이트 JSON + 글 초안 생성
posts/                  생성된 블로그 글 초안 (`[직접 작성]` 부분은 사람이 채움)
output/charts/          생성된 차트 PNG
site/
  index.html             웹사이트 본체 — 탭: 한눈에(홈)/순위 분석/연재 글/소개 등
  data/                  run.py가 자동 생성하는 JSON/JS (fixtures.js, forecast_log.js, standings.js 등)
  vendor/                차트 라이브러리(Chart.js)
```

**`site/index.html`이 실제 배포되는 홈페이지다.** 더블클릭하면 로컬에서 바로 열림. `git push`하면 GitHub Pages(`https://<계정>.github.io/kfootball-lab/site/`)에도 자동 반영됨 — khu-soccer-site와 달리 여기는 별도 수동 배포 단계가 없음.

## 데이터 상태

- `data/raw/`에 이미 실제 데이터(matches.csv, daegu2026/, race_h2h_*, attendance2026/ 등)가 들어있음 — README의 "지금은 샘플 데이터" 설명은 초기 세팅 시점 얘기이고, **현재는 실 데이터 단계로 넘어갔음**. 실제 코드/데이터를 항상 우선해서 확인할 것.
- `match_id`가 모든 CSV에서 정확히 일치해야 연결됨.
- 표본이 작은 분석(On/Off 등)은 반드시 한계를 같이 명시하는 게 이 프로젝트의 원칙.

## 저작권 제약 (중요)

- 선수 **사진**, 구단 **엠블럼**, 경기 **영상** 사용 금지 — 이름/등번호와 직접 그린 다이어그램만 사용.
- 데이터 출처와 수집일을 모든 글/사이트에 표기.

## 작업 방식

- **원칙: 숫자와 차트는 자동, 해석과 의견은 사람이 직접.** 글 초안의 `[직접 작성]` 부분을 대신 채워 넣지 말 것.
- 블로그 발행은 이 프로젝트가 아니라 별도 `blog-automation`(`C:\dev\blog-automation`) 파이프라인을 통해서 함: `python run.py` → `posts/`의 `.md` 완성 → 차트 PNG를 네이버 에디터에 붙여넣기 → `blog-automation`으로 발행.
- `C:\dev\kfootball-dashboard-demo`는 이 사이트(`site/index.html`)의 UI를 다시 디자인해보는 **별도 Next.js 프로토타입/데모**임. 아직 이 프로젝트 본체에 병합된 건 아님 — 관계와 현재 상태는 `HANDOFF.md` 참고.
- 세션을 시작할 때 `HANDOFF.md`를 먼저 읽고, 끝날 때 갱신할 것.
