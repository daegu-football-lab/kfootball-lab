// 대구 풋볼 랩 화면 코드 (11/21 index.html 에서 분리).
// 데이터 파일(site/data/*.js)이 먼저 로드된 뒤 실행되어야 하므로 index.html 맨 아래에서 부릅니다.
// 축구 백과 항목(GLOSSARY)도 이 파일에 있습니다.
const D = window.KFL_DATA;
let chartT = null, chartO = null;
const sel = [];   // 선수 탭에서 선택된 선수 (최대 2명)

const fmt = n => (n === null || n === undefined || Number.isNaN(n)) ? "-" :
  (typeof n === "number" ? (Number.isInteger(n) ? n : n.toFixed(2)) : n);

// 팀 이름 앞 원형 배지. 구단 엠블럼은 상표권 문제가 있어 쓰지 않고
// 팀 컬러 + 이니셜로 대체합니다(README 저작권 주의 참고).
//   c = 주색(원 안), s = 보조색(바깥 테두리, 없으면 회색 테두리), t = 글자색(기본 흰색)
// 출처: 각 구단 나무위키 '상징색' 항목 (2026-09-27 확인).
//   Pantone·CMYK로만 적힌 색은 화면용 hex로 근사 변환했습니다.
//   대구FC·파주프런티어(블루)·김포FC·충남아산은 hex가 없어 이름만 보고 고른 근사치입니다.
// 노란 주색(전남)은 흰 글자가 안 읽혀서 글자를 어둡게 둡니다.
const TEAM_META = {
  "수원삼성":     {c:"#1C4DA1", s:"#D7263D", i:"삼성"},   // 파랑·흰색·빨강
  "수원FC":       {c:"#D0273C", s:"#1C3F94", i:"수원"},   // 빨강·파랑 줄무늬
  "서울이랜드":   {c:"#1B2A5A", s:"#C9A646", i:"서울"},   // 진청(네이비)·황금·파랑
  "대구FC":       {c:"#2EA3E8", i:"대구"},                 // 하늘색
  "화성FC":       {c:"#E8551E", s:"#2359BD", i:"화성"},   // 주황 RGB(232,85,30)·남색
  "부산아이파크": {c:"#DA291C", s:"#54585A", i:"부산"},   // HDC 레드(485C)·HDC 그레이
  "김포FC":       {c:"#0B5E3A", s:"#C9A646", i:"김포"},   // 진녹색·금색
  "충남아산":     {c:"#1D5FAF", s:"#F5C400", i:"아산"},   // 서해 파랑·은행나무 노랑
  "경남FC":       {c:"#E83827", s:"#FFD404", i:"경남"},   // 레드 RGB(232,56,39)·옐로
  "성남FC":       {c:"#111111", i:"성남"},                 // 검정·흰색
  "충북청주":     {c:"#1C235A", s:"#E8383D", i:"청주"},   // 진청 RGB(28,35,90)·빨강
  "파주프런티어": {c:"#1F4E9C", s:"#E86FA4", i:"파주"},   // 프런티어 블루·코스모스 핑크
  "용인FC":       {c:"#A6093D", s:"#5BC2E7", i:"용인"},   // 미르 레드 RGB(166,9,61)·셀레스철 블루
  "천안시티":     {c:"#5EB3E4", i:"천안"},                 // 천안 스카이블루 #5EB3E4
  "안산그리너스": {c:"#00A77E", s:"#FFDF2B", i:"안산"},   // 그린·옐로
  "전남드래곤즈": {c:"#FFD200", s:"#111111", t:"#111111", i:"전남"}, // 노랑·검정
  "김해FC":       {c:"#CB171A", s:"#F49B00", i:"김해"},   // 레드 #CB171A·골드 #F49B00
};
const teamBadge = name => {
  const m = TEAM_META[name];
  if(!m) return `<span class="tname"><span>${name}</span></span>`;
  // 보조색이 있으면 바깥 테두리로 보여 줍니다(안쪽 2px은 배경색 틈).
  const ring = m.s ? `;box-shadow:0 0 0 2px var(--card),0 0 0 4px ${m.s}` : "";
  const st = `background:${m.c};color:${m.t || "#fff"}${ring}`;
  return `<span class="tname"><span class="tbadge" style="${st}">${m.i}</span><span>${name}</span></span>`;
};

// ── 초기화 ────────────────────────────────────────────────────
function init(){
  if(!D){ document.getElementById("sub").textContent =
    "데이터가 없습니다. 먼저 python run.py 를 실행하세요."; return; }

  // 헤더의 경기 수.
  //   D.matches 는 '대구 경기 기록 CSV'의 줄 수인데, 지금은 샘플이라 16입니다.
  //   팀 시즌 누적(team_season_stats.csv)이 있으면 그쪽 경기 수가 진짜입니다.
  //   샘플 숫자를 헤더에 띄우면 방문자가 실제 기록으로 착각합니다.
  const myRow = (D.teams || []).find(t => t.team === D.meta.team);
  const games = (D.meta.team_is_real && myRow) ? myRow.경기수 : D.matches.length;
  document.getElementById("sub").textContent =
    `${D.meta.season}시즌 · ${D.meta.team} ${games}경기 · 생성일 ${D.meta.generated_at}`;
  // 어느 데이터가 진짜이고 어느 것이 아직 샘플인지 정확히 알려줍니다.
  // (샘플 숫자를 실제로 착각해서 글에 쓰는 사고를 막기 위한 장치)
  // 배너는 '방문자가 읽어야 할 것'만 담습니다.
  // 개발자용 할 일 안내(어느 CSV를 채워라 등)는 화면이 아니라 콘솔로 보냅니다.
  // 화면에 남겨 두면 방문자에게는 미완성 페이지로 보입니다.
  const lines = [];
  if (D.meta.is_sample) {
    console.warn(
      "[KFL] 선수/On-Off 데이터가 아직 샘플입니다. " +
      "data/raw/ 에 실제 경기 기록을 넣고 다시 실행하면 해당 탭이 다시 나타납니다."
    );
  }
  // 출처 문구는 화면 맨 아래(푸터)와 순위 기준일 줄에 있으므로 첫 화면 상자에서는 뺍니다.
  if (!D.meta.team_is_real) {
    lines.push("ℹ️ 팀 비교는 <b>대구전 표본</b> 기준이라 왜곡될 수 있습니다.");
    console.warn(
      "[KFL] data/raw/team_season_stats.csv 를 채우면 리그 전체 순위표가 됩니다."
    );
  }
  const bannerEl = document.getElementById("banner");
  bannerEl.innerHTML = lines.join("<br>");
  // 띄울 내용이 없으면 빈 상자가 남지 않도록 배너 자체를 감춥니다.
  bannerEl.style.display = lines.length ? "" : "none";

  // 샘플(가짜) 데이터인 동안에는 선수·On/Off 탭 버튼을 감춥니다.
  // 배너 경고만으로는 방문자가 가짜 이름을 실제 기록으로 캡처해 갈 위험이 남습니다.
  // 실제 기록을 넣어 is_sample 이 false 가 되면 자동으로 다시 나타나므로,
  // "나중에 되돌리기"를 잊어버릴 일이 없습니다.
  if (D.meta.is_sample) {
    ["p", "o"].forEach(k => {
      const btn = document.querySelector(`nav button[data-t="${k}"]`);
      if (btn) btn.style.display = "none";
    });
  }

  buildCards(); buildTeamTab(); buildOnOffTab(); buildStandingsTab();
  buildGlossary();
  buildHome();
  buildHomeCards();
  buildOddsTab();
  buildPossession();
  // initMode();  // 쉽게/자세히 토글은 없앴습니다 (2026-09-28). 함수는 되돌릴 때를 위해 남겨 둠
  linkTerms();     // 본문 용어에 점선 긋기
  initTips();      // 점선 단어 눌렀을 때 뜨는 말풍선
  syncTableHints();

  document.querySelectorAll("nav button").forEach(b=>{
    b.onclick = () => {
      document.querySelectorAll("nav button").forEach(x=>x.classList.remove("on"));
      document.querySelectorAll(".panel").forEach(x=>x.classList.remove("on"));
      b.classList.add("on");
      document.getElementById("pan-"+b.dataset.t).classList.add("on");
      // 숨겨져 있던 탭은 display:none 상태라 표 너비가 0으로 잡혀서
      // 스크롤 필요 여부를 미리 알 수 없습니다. 탭이 실제로 보인 다음에
      // 다시 재봐야 정확합니다.
      syncTableHints();
    };
  });

  window.addEventListener("resize", syncTableHints);

  // 주소 끝에 #tab=b 처럼 붙이면 그 탭으로 바로 엽니다 (블로그 글에서 링크할 때 사용).
  const m = (location.hash || "").match(/^#tab=([a-z])$/);
  if (m) switchTab(m[1]);
}

// 가로 스크롤이 실제로 되는 표에만 "옆으로 밀면 더 보입니다" 힌트를 켭니다.
// 표 옆에 나란히 둔 .tblhint 하나씩을 짝지어 확인합니다.
function syncTableHints(){
  document.querySelectorAll(".tbl").forEach(tbl => {
    const hint = tbl.nextElementSibling;
    if(!hint || !hint.classList.contains("tblhint")) return;
    hint.classList.toggle("show", tbl.scrollWidth > tbl.clientWidth + 1);
  });
}

// 한 번이라도 옆으로 민 표는 더 보여줄 필요가 없으니 그 힌트만 끕니다.
// 위임(delegation)을 쓰는 이유: 표 자체(.tbl)는 스크롤 컨테이너라 매번
// 새로 만들지 않고 그대로 있으므로, 페이지 전체에 한 번만 걸어 두면 됩니다.
document.addEventListener("scroll", e => {
  const tbl = e.target.closest && e.target.closest(".tbl");
  if(!tbl) return;
  const hint = tbl.nextElementSibling;
  if(hint && hint.classList.contains("tblhint")) hint.classList.remove("show");
}, true);

// ── 탭 1: 선수 ────────────────────────────────────────────────
function buildCards(){
  const box = document.getElementById("cards");
  const src = document.getElementById("psrc");
  if(src && D.meta.players_matches)
    src.textContent = `· 대구 ${D.meta.players_matches}경기 기준, ${D.meta.players_source || ""}`;
  box.innerHTML = D.players.map(p => `
    <div class="card" data-n="${p.player}">
      <div class="nm">${p.player}</div>
      <div class="po">${p.포지션 ?? ""}</div>
      <div class="mt">${p.출전경기}경기 · ${p.출전시간}분</div>
      <div class="mt">골 ${p.골} · 도움 ${p.도움}</div>
    </div>`).join("");

  box.querySelectorAll(".card").forEach(c => {
    c.onclick = () => {
      const n = c.dataset.n, i = sel.indexOf(n);
      if(i >= 0) sel.splice(i,1);
      else { sel.push(n); if(sel.length > 2) sel.shift(); }
      box.querySelectorAll(".card").forEach(x =>
        x.classList.toggle("sel", sel.includes(x.dataset.n)));
      renderPlayers();
    };
  });
}

// 매치센터 경기 기록에 있는 것만 씁니다(패스·태클 같은 세부 기록은 화면에 없음).
const P90 = [
  ["골_per90","골"], ["도움_per90","도움"], ["공격포인트_per90","공격포인트(골+도움)"],
];
// 출전 시간이 짧으면 90분당 수치가 크게 흔들립니다(예: 30분 뛰고 1골 → 90분당 3골).
const MIN_MINUTES = 450;  // 5경기 풀타임
const smallNote = p => p.출전시간 < MIN_MINUTES
  ? `<div class="warn">출전 ${p.출전시간}분으로 짧습니다. 90분당 수치는 몇 번의 장면에 크게 흔들립니다.</div>` : "";

function renderPlayers(){
  const el = document.getElementById("pdetail");
  if(sel.length === 0){ el.innerHTML = '<p class="empty">선수를 선택하세요.</p>'; return; }
  const picks = sel.map(n => D.players.find(p => p.player === n));

  if(picks.length === 1){
    const p = picks[0];
    el.innerHTML = `<h2>${p.player} <span style="color:var(--muted);font-weight:400">
      ${p.포지션 ?? ""}</span></h2>
      <div class="stats">
        <div class="stat"><b>${p.출전경기}</b><span>출전</span></div>
        <div class="stat"><b>${p.선발}</b><span>선발</span></div>
        <div class="stat"><b>${p.출전시간}</b><span>출전 분</span></div>
        <div class="stat"><b>${p.공격포인트}</b><span>공격포인트</span></div>
      </div>
      <p class="hint">아래는 <b>90분당</b> 기록입니다. 출전 시간이 다른 선수끼리
        공정하게 비교하기 위한 보정입니다.</p>
      <table><thead><tr><th>지표</th><th>90분당</th><th>시즌 합계</th></tr></thead><tbody>
      ${P90.map(([k,label]) => `<tr><td>${label}</td><td>${fmt(p[k])}</td>
        <td>${fmt(p[k.replace("_per90","").replace("(골+도움)","")])}</td></tr>`).join("")}
      <tr><td>경고 / 퇴장</td><td>—</td><td>${p.경고} / ${p.퇴장}</td></tr>
      </tbody></table>
      ${smallNote(p)}
      <p class="hint" style="margin-top:12px">${(D.meta.players_note || "")}</p>
      <p class="hint">비교하려면 다른 선수를 하나 더 누르세요.</p>`;
    return;
  }

  const [a,b] = picks;
  el.innerHTML = `<h2>${a.player} vs ${b.player}</h2>
    <p class="hint">둘 다 90분당 기록입니다. 초록색이 더 높은 쪽입니다.</p>
    <table><thead><tr><th>지표</th><th>${a.player}</th><th>${b.player}</th>
      <th>차이</th></tr></thead><tbody>
    ${P90.map(([k,label]) => {
      const x = a[k] ?? 0, y = b[k] ?? 0, d = (x-y).toFixed(2);
      return `<tr><td>${label}</td>
        <td class="${x>y?'up':''}">${fmt(x)}</td>
        <td class="${y>x?'up':''}">${fmt(y)}</td>
        <td>${d>0?'+':''}${d}</td></tr>`;
    }).join("")}
    <tr><td>출전 시간(분)</td><td>${a.출전시간}</td><td>${b.출전시간}</td>
      <td>${a.출전시간-b.출전시간>0?'+':''}${a.출전시간-b.출전시간}</td></tr>
    </tbody></table>
    ${smallNote(a)}${smallNote(b)}
    <p class="hint">포지션이 다르면 공격포인트로 비교하는 것 자체가 맞지 않을 수 있습니다(수비수·골키퍼).</p>`;
}

// ── 탭 2: 팀 비교 ─────────────────────────────────────────────
// 표에 보여줄 팀 지표 컬럼을 데이터에서 자동으로 뽑습니다.
// 시즌 누적 파일(team_season_stats.csv)을 넣으면 승점·득실차 컬럼이 생기는데,
// 이렇게 해두면 사이트 코드를 고치지 않아도 새 컬럼이 자동으로 표에 나타납니다.
const SKIP_COLS = ["team","경기수","출처"];
const RAW_COLS = D && D.teams && D.teams.length
  ? Object.keys(D.teams[0]).filter(k => !SKIP_COLS.includes(k))
  : [];

// '경기당' 지표를 앞으로 보냅니다.
//   승/무/패/승점/득실차는 '누적'이라, 경기 수가 다른 팀끼리 비교하면 착시가 생깁니다.
//   기본값이 누적 지표면 방문자가 가장 먼저 보는 그래프가 불공정해집니다.
const isPerGame = c => c.startsWith("경기당");
const TEAM_COLS = [...RAW_COLS.filter(isPerGame), ...RAW_COLS.filter(c => !isPerGame(c))];
const colLabel = c => isPerGame(c) ? c.replace(/_/g," ") : c.replace(/_/g," ") + " (누적)";

// 팀 비교 탭 아래 '대구FC 점유율과 성적' (data/possession.js = card_possession.py 가 만든 집계값)
function buildPossession(){
  const box = document.getElementById("pz");
  const P = window.KFL_POSSESSION;
  if (!box) return;
  if (!P) { box.style.display = "none"; return; }
  const keys = Object.keys(P.groups);           // ["전체", "김병수", "최성용"]
  const few = n => n < P.meta.small_n ? '<span class="pz-few">표본 적음</span>' : "";

  // 막대 한 줄: 라벨 | 막대(+기준 점선) | 숫자
  const row = (label, value, max, ref, hi, numHtml) => {
    const w = value == null ? 0 : Math.min(100, value / max * 100);
    return `<div class="pz-row"><span>${label}</span>
      <div class="pz-track"><div class="pz-fill${hi ? " hi" : ""}" style="width:${w}%"></div>
        <i class="pz-ref" style="left:${ref / max * 100}%"></i></div>
      <span class="pz-num">${numHtml}</span></div>`;
  };

  function render(key){
    const g = P.groups[key];
    document.getElementById("pz-sum").innerHTML =
      `<b>${key}</b> ${g.games}경기 · 경기당 승점 <b>${g.ppg.toFixed(2)}</b> · 평균 점유율 <b>${g.poss.toFixed(1)}%</b>${few(g.games)}`;
    document.getElementById("pz-bins").innerHTML = g.bins.map((b, i) =>
      row(b.label, b.ppg, 3, g.ppg, i === g.bins.length - 1,
        b.n ? `<b>${b.ppg.toFixed(2)}</b>${few(b.n)}<small>${b.n}경기 · ${b.w}승 ${b.d}무 ${b.l}패</small>`
            : `<small>경기 없음</small>`)).join("");
    document.getElementById("pz-states").innerHTML = g.states.map((s, i) =>
      row(s.label, s.poss, 75, 50, i === g.states.length - 1,
        s.intervals ? `<b>${s.poss.toFixed(1)}%</b><small>${s.intervals}개 구간</small>` : `<small>구간 없음</small>`)).join("");
    seg.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.k === key));
  }

  const seg = document.getElementById("pz-seg");
  seg.innerHTML = keys.map(k => `<button type="button" data-k="${k}">${k}${k === "전체" ? "" : " 감독"}</button>`).join("");
  seg.addEventListener("click", e => { const b = e.target.closest("button"); if (b) render(b.dataset.k); });
  document.getElementById("pz-asof").textContent =
    `${P.meta.round}라운드 종료 기준 (대구 ${P.meta.games}경기) · ${P.meta.source} · 본 분석에 사용된 데이터의 저작권 및 소유권은 한국프로축구연맹(K LEAGUE)에 있습니다.`;
  render("전체");
}

function buildTeamTab(){
  const s = document.getElementById("tmetric");
  s.innerHTML = TEAM_COLS.map(c =>
    `<option value="${c}">${colLabel(c)}</option>`).join("");
  s.onchange = drawTeam;
  drawTeam();

  const head = ["순위","팀","경기수",...TEAM_COLS];
  document.getElementById("ttable").innerHTML =
    `<thead><tr>${head.map(h=>`<th>${["순위","팀","경기수"].includes(h)
        ? h : colLabel(h)}</th>`).join("")}</tr></thead>
     <tbody>${D.teams.map((t,i) => `<tr class="${t.team===D.meta.team?'mine':''}">
       <td>${i+1}</td><td>${teamBadge(t.team)}</td><td>${t.경기수}</td>
       ${TEAM_COLS.map(c=>`<td>${fmt(t[c])}</td>`).join("")}</tr>`).join("")}</tbody>`;
}

function drawTeam(){
  const m = document.getElementById("tmetric").value;

  // '실점'이 들어간 지표는 낮을수록 좋으므로 오름차순으로 정렬합니다.
  // 그래야 막대 맨 위(1위)가 항상 '가장 좋은 팀'이 됩니다.
  // '많을수록 좋은' 지표와 '적을수록 좋은' 지표를 구분해 정렬 방향을 바꿉니다.
  // 이걸 안 하면 패·실점 같은 지표에서 가장 나쁜 팀이 맨 위에 옵니다.
  const lowerIsBetter = ["실점", "패", "파울"].some(k => m.includes(k));
  const rows = [...D.teams].sort((a,b)=> lowerIsBetter ? a[m]-b[m] : b[m]-a[m]);

  // 가로 막대는 팀 수만큼 세로 공간이 필요합니다.
  // 높이를 고정해두면 Chart.js가 축 라벨을 몇 개 건너뛰어 팀 이름이 사라집니다.
  document.getElementById("tchart").parentElement.style.height =
    (rows.length * 26 + 70) + "px";

  if(chartT) chartT.destroy();
  chartT = new Chart(document.getElementById("tchart"), {
    type:"bar",
    // 막대가 17개라 이름만으로는 몇 번째인지 세기 어렵습니다. 순번을 앞에 붙입니다.
    // '1위'가 아니라 '1.' 인 이유: 이건 리그 순위가 아니라 '고른 지표' 기준 줄 순서입니다.
    data:{ labels: rows.map((r,i)=>`${i+1}. ${r.team}`),
      datasets:[{ data: rows.map(r=>r[m]),
        backgroundColor: rows.map(r => r.team===D.meta.team ? "#2ea3e8" : "#c9d6e4"),
        borderRadius:4 }]},
    options:{ maintainAspectRatio:false, indexAxis:"y",
      plugins:{legend:{display:false},
        title:{display:true,text:colLabel(m)}},
      scales:{
        x:{grid:{color:"#eef2f6"}},
        // crossAlign:"far" = 팀 이름을 축에서 먼 쪽(왼쪽)에 맞춰 한 줄로 세웁니다.
        // 기본값(near)은 축에 붙여 오른쪽 정렬이라 이름 길이에 따라 들쭉날쭉해집니다.
        y:{grid:{display:false},
           ticks:{crossAlign:"far", padding:6, font:{size:12}}}}}
  });
}

// ── 탭 0: 순위 분석 ───────────────────────────────────────────
let chartS = null;

function buildStandingsTab(){
  const S = window.KFL_STANDINGS;

  // 데이터가 없으면 탭 자체를 숨깁니다.
  // (있는 척하고 빈 화면을 보여주는 것보다, 없는 게 낫습니다)
  if(!S){
    // 홈 탭이 기본으로 켜져 있으므로 순위 탭 버튼만 감추면 됩니다.
    document.querySelector('nav button[data-t="s"]').style.display = "none";
    document.getElementById("pan-s").classList.remove("on");
    return;
  }

  const sig = S.teams.filter(t => t.유의);
  // 요약 카드: R²·σ 같은 통계 기호는 쓰지 않고 뜻으로 풀어 씁니다.
  // '크게 벗어남' 기준은 연재 1편과 같은 1.5σ (표본 17팀이라 그보다 작으면 해석하지 않음)
  // (원래 숫자는 아래 그래프 '읽는 법'과 순위표의 잔차 칸에 그대로 있습니다)
  const me  = S.teams.find(t => t.team === S.meta.team);
  const sigTxt = sig.map(t => `${t.team}(${t.시그마 > 0 ? "더 많이" : "더 적게"})`).join(", ");
  const meTxt = !me ? "-" : (Math.abs(me.시그마) < 1.5 ? "예상과 비슷"
                   : (me.시그마 > 0 ? "예상보다 많이" : "예상보다 적게"));
  document.getElementById("s-summary").innerHTML = `
    <div class="stat"><b>${Math.round(S.reg.r2 * 100)}%</b><span>득실차로 설명되는 승점<br>100%에 가까울수록 골 득실만큼 승점을 땄다는 뜻</span></div>
    <div class="stat"><b>${meTxt}</b><span>${S.meta.team}가 딴 승점<br>득실차로 예상한 승점과 비교</span></div>
    <div class="stat"><b>${sig.length}팀</b><span>예상에서 크게 벗어난 팀<br>${sigTxt || "없음"}</span></div>
    <div class="stat"><b>${S.race.잔여경기}경기</b><span>${S.meta.team} 남은 경기</span></div>`;

  drawScatter(S);

  // 순위표
  document.getElementById("stable").innerHTML = `
    <thead><tr><th>PPG순위</th><th>팀</th><th>경기</th><th>승점</th><th>경기당 승점</th>
      <th>득실차</th><th>공식순위</th><th>변동</th><th>평균선과<br><small>1.5↑ = ★</small></th>
      <th>더/덜 번<br>승점</th></tr></thead>
    <tbody>${[...S.teams].sort((a,b)=>a.PPG순위-b.PPG순위).map(t => {
      const mv = t.순위변동;
      const mvs = mv === 0 ? "-" : (mv > 0 ? `▲${mv}` : `▼${-mv}`);
      return `<tr class="${t.team===S.meta.team?'mine':''}">
        <td>${t.PPG순위}</td><td>${teamBadge(t.team)}</td><td>${t.경기수}</td><td>${t.승점}</td>
        <td>${t.PPG.toFixed(3)}</td><td>${t.득실차>0?'+':''}${t.득실차}</td>
        <td>${t.총점순위}</td><td>${mvs}</td>
        <td style="${t.유의 ? 'font-weight:700' : ''}"
          >${t.유의 ? (t.시그마>0 ? '▲ ' : '▼ ') : ''}${t.시그마>0?'+':''}${t.시그마}${t.유의?' ★':''}</td>
        <td>${t.잔차_시즌환산 == null ? "-" : (t.잔차_시즌환산 > 0 ? "+" : "") + t.잔차_시즌환산 + "점"}</td></tr>`;
    }).join("")}</tbody>`;

  // 시나리오 표
  //   JSON 키를 그대로 헤더에 쓰면 "필요 최소 승수(무승부 0 가정)" 처럼 길어
  //   칸이 제멋대로 늘어납니다. 짧은 제목 + 작은 설명으로 두 줄로 나눕니다.
  const rows = S.race.시나리오;
  if(rows.length){
    // 열 이름은 export.py 가 만든 한글 키입니다. 끝말로 찾아 두면 팀이 바뀌어도 그대로 동작합니다.
    const cols  = Object.keys(rows[0]);
    const kLeft = cols.find(c => c.endsWith("잔여승점"));
    const kFin  = cols.find(c => c.endsWith("최종"));
    const kNeed = cols.find(c => c.endsWith("필요승점"));
    const kWin  = cols.find(c => c.startsWith("필요 최소"));
    const OX    = cols[cols.length - 1];
    const rival = S.race.핵심경쟁팀, me2 = S.meta.team, myLeft = S.race.잔여경기;
    // 승점을 '몇 승'으로 바꿔 읽습니다. 3의 배수가 아니면(무승부 섞임) 승점만 씁니다.
    const asWins = p => p % 3 === 0 ? `${p / 3}승` : `${p}점`;
    const rivalLeft = Math.max(...rows.map(r => r[kLeft])) / 3;

    document.getElementById("s-race-lead").innerHTML =
      `확률이 아니라 단순 계산입니다. 지금 2위 <b>${rival}</b>가 남은 ${rivalLeft}경기에서 몇 번 이기느냐에 따라,
       <b>${me2}</b>가 남은 ${myLeft}경기에서 몇 번 이겨야 ${rival}보다 위에 서는지가 달라집니다.
       (무승부 없이 승리만 센 경우)` +
      (rows[2] ? `<br>예) ${rival}가 <b>${asWins(rows[2][kLeft])}</b> 하면 → ${me2}는 <b>${rows[2][kWin]}승 이상</b> 필요` : "");

    const lastOk = rows.map(r => r[OX]).lastIndexOf("O");
    document.getElementById("srace").innerHTML =
      `<thead><tr>
         <th>${teamBadge(rival)}<small>남은 경기 성적</small></th>
         <th>${teamBadge(rival)}<small>최종 승점</small></th>
         <th>${teamBadge(me2)}<small>필요한 성적 (남은 ${myLeft}경기)</small></th>
         <th>가능?</th></tr></thead>
       <tbody>${rows.map((r, i) => {
         const dead = r[OX] === "X";
         const cls  = [dead ? "dead" : "", i === lastOk ? "edge" : ""].filter(Boolean).join(" ");
         return `<tr class="${cls}">
           <td><b>${asWins(r[kLeft])}</b><small>+${r[kLeft]}점</small></td>
           <td>${r[kFin]}점</td>
           <td><b>${r[kWin]}승 이상</b><small>+${r[kNeed]}점</small></td>
           <td><span class="ox ${dead ? "no" : "yes"}">${dead ? "✕ 불가" : "○ 가능"}</span></td></tr>`;
       }).join("")}</tbody>`;
  }

  document.getElementById("s-note").innerHTML =
    `${S.meta.team}는 현재 <b>${S.race.현재승점}점</b>, 잔여 ${S.race.잔여경기}경기로
     산술적 최대 <b>${S.race.최대가능승점}점</b>입니다.
     이 표는 2위 팀(${S.race.핵심경쟁팀})만 상대로 계산한 것이라,
     통과해도 2위가 보장되지는 않습니다. ·
     일정 난이도(상대 전력)는 보정하지 않았습니다. ·
     출처: ${S.meta.출처}, 기준일은 글에 표기.`;

  renderGamesPlayed(S);
  renderPace(S);
  renderRemaining();
}

// ① 보충: 왜 경기 수가 섞여 있는가 (연재 1편 1장)
//   팀 수·경기 수를 데이터에서 세므로, 라운드가 진행돼도 손으로 고칠 곳이 없습니다.
function renderGamesPlayed(S){
  const el = document.getElementById("s-gp");
  if(!el) return;
  const n = S.teams.length;
  const perTeam = 2 * (n - 1);              // 2로빈: 나머지 모든 팀과 두 번씩
  const groups = {};                        // { 25: ["수원삼성", ...], 26: [...] }
  S.teams.forEach(t => (groups[t.경기수] = groups[t.경기수] || []).push(t.team));
  const lines = Object.keys(groups).map(Number).sort((a, b) => a - b).map(g =>
    `<li><b>${g}경기</b> 치른 팀 ${groups[g].length}개 — ${groups[g].map(esc).join(", ")}</li>`).join("");
  const odd = n % 2 === 1;
  el.innerHTML = `
    <p style="margin:6px 0">K리그2는 <b>${n}팀</b>이 모든 팀과 홈·원정 한 번씩 맞붙는
      <span class="term" data-g="2로빈">2로빈</span>이라, 한 팀이 치르는 경기는 <b>${perTeam}경기</b>입니다.
      ${odd ? `팀 수가 홀수라 <b>매 라운드 한 팀은 쉽니다.</b> 그래서 같은 라운드가 끝나도 팀마다 치른 경기 수가 다릅니다.` : ""}</p>
    <ul style="margin:6px 0 8px;padding-left:20px">${lines}</ul>
    <p style="margin:6px 0">한 경기에는 최대 3점이 걸려 있어서, 총 승점을 그대로 비교하면 한 경기 덜 치른 팀이 불리해 보입니다.
      그래서 이 탭은 승점을 경기 수로 나눈 <span class="term" data-g="PPG (경기당 승점)">경기당 승점</span>으로 줄을 다시 세웁니다.</p>
    <p style="margin:6px 0;color:var(--muted)">다만 경기당으로 나눠도, 아직 안 치른 경기의 상대가 강한지 약한지는 반영되지 않습니다.</p>`;
}

// ③ 보충: 페이스대로 가면 최종 승점 (연재 1편 4장)
//   최종 추정 = 현재 승점 + 경기당 승점 × 남은 경기. 확률이 아닌 단순 곱셈입니다.
//   상위 6팀(자동 승격 + 플레이오프권)만 보여 줍니다.
//   휴대폰에서 표가 잘려도 핵심 숫자가 먼저 보이도록 추정·최대 승점을 팀 바로 옆에 둡니다.
function renderPace(S){
  const el = document.getElementById("space");
  if(!el) return;
  const perTeam = 2 * (S.teams.length - 1);
  const top = [...S.teams].sort((a, b) => a.총점순위 - b.총점순위).slice(0, 6);
  el.innerHTML = `
    <thead><tr><th>팀<br><small>현재 순위 순</small></th>
      <th>페이스대로 가면<br><small>최종 승점 추정</small></th><th>전승하면<br><small>최대 승점</small></th>
      <th>현재 승점</th><th>남은 경기</th></tr></thead>
    <tbody>${top.map(t => {
      const left = perTeam - t.경기수;
      const pace = t.승점 + t.PPG * left;
      return `<tr class="${t.team === S.meta.team ? "mine" : ""}">
        <td>${teamBadge(t.team)}</td>
        <td><b>${pace.toFixed(1)}점</b></td><td>${t.승점 + left * 3}점</td>
        <td>${t.승점}</td><td>${left}</td></tr>`;
    }).join("")}</tbody>`;
}

function drawScatter(S){
  const xs = S.teams.map(t=>t.경기당득실차);
  const lo = Math.min(...xs) - 0.1, hi = Math.max(...xs) + 0.1;
  const line = x => S.reg.intercept + S.reg.slope * x;
  const sd = S.reg.resid_sd;

  const pts = S.teams.map(t => ({x:t.경기당득실차, y:t.PPG, t}));
  const color = t => t.team === S.meta.team ? "#2ea3e8"
                   : t.유의 ? "#e4572e" : "#c9d6e4";

  // Chart.js 에는 점 옆에 글자를 쓰는 기능이 없습니다.
  // 라이브러리를 하나 더 받는 대신, 그리기가 끝난 뒤 직접 글자를 얹는
  // 작은 플러그인을 만들어 씁니다. (의존성을 늘리지 않는 쪽을 택했습니다)
  const labelPlugin = {
    id: "ptLabels",
    afterDatasetsDraw(c){
      const i = c.data.datasets.length - 1;      // 마지막 = 팀 점들
      const ds = c.data.datasets[i], meta = c.getDatasetMeta(i);
      const ctx = c.ctx;
      ctx.save();
      ctx.font = "600 11px system-ui, sans-serif";
      ctx.fillStyle = "#33415c";
      meta.data.forEach((pt, k) => {
        const t = ds.data[k].t;
        if(!t || !(t.유의 || t.team === S.meta.team)) return;   // 겹침 방지
        const txt = t.team + (t.유의 ? " ★" : "");
        // 오른쪽에 공간이 없으면 왼쪽에 씁니다
        const w = ctx.measureText(txt).width;
        const right = pt.x + 12 + w < c.chartArea.right;
        ctx.textAlign = right ? "left" : "right";
        ctx.fillText(txt, pt.x + (right ? 12 : -12), pt.y + 4);
      });
      // 구역 이름표. '운이 좋다/나쁘다' 같은 원인 단정은 쓰지 않습니다.
      const A = c.chartArea;
      ctx.font = "600 12px system-ui, sans-serif";
      ctx.fillStyle = "#8a97a8";
      ctx.textAlign = "left";
      ctx.fillText("↖ 득실차에 비해 승점이 많음", A.left + 8, A.top + 16);
      ctx.textAlign = "right";
      ctx.fillText("득실차에 비해 승점이 적음 ↘", A.right - 8, A.bottom - 10);
      ctx.restore();
    }
  };

  if(chartS) chartS.destroy();
  chartS = new Chart(document.getElementById("schart"), {
    type:"scatter",
    plugins:[labelPlugin],
    data:{ datasets:[
      // 띠는 먼저 그려야 점 아래에 깔립니다.
      { label:`+1σ`, type:"line", data:[{x:lo,y:line(lo)+sd},{x:hi,y:line(hi)+sd}],
        borderColor:"rgba(0,0,0,0)", pointRadius:0, fill:"+1",
        backgroundColor:"rgba(136,136,136,.12)" },
      { label:`−1σ`, type:"line", data:[{x:lo,y:line(lo)-sd},{x:hi,y:line(hi)-sd}],
        borderColor:"rgba(0,0,0,0)", pointRadius:0 },
      { label:`추세선 (R²=${S.reg.r2})`, type:"line",
        data:[{x:lo,y:line(lo)},{x:hi,y:line(hi)}],
        borderColor:"#888", borderWidth:1.5, pointRadius:0 },
      { label:"팀", data:pts,
        pointBackgroundColor: pts.map(p=>color(p.t)),
        pointBorderColor:"#fff", pointBorderWidth:1.5,
        pointRadius: pts.map(p=> p.t.team===S.meta.team ? 9 : (p.t.유의 ? 7 : 5)) },
    ]},
    options:{ maintainAspectRatio:false,
      plugins:{
        legend:{display:false},
        tooltip:{ callbacks:{ label: c => {
          const t = c.raw.t; if(!t) return "";
          return `${t.team} · 경기당 승점 ${t.PPG.toFixed(2)} · ` +
            (Math.abs(t.시그마) < 1.5 ? "흔한 차이" : (t.시그마 > 0 ? "득실차보다 승점 많음" : "득실차보다 승점 적음"));
        }}},
      },
      scales:{
        x:{ title:{display:true,text:"경기당 득실차"}, grid:{color:"#eef2f6"} },
        y:{ title:{display:true,text:"경기당 승점 (PPG)"}, grid:{color:"#eef2f6"} }
      }}
  });
}

// ── 탭 3: On/Off ──────────────────────────────────────────────
function buildOnOffTab(){
  const names = Object.keys(D.onoff || {});
  const s = document.getElementById("osel");
  if(names.length === 0){
    document.getElementById("obody").innerHTML =
      '<p class="empty">출전·결장이 모두 있는 선수가 없어 비교할 수 없습니다.</p>';
    return;
  }
  s.innerHTML = names.map(n=>`<option>${n}</option>`).join("");
  s.onchange = drawOnOff;
  drawOnOff();
}

function drawOnOff(){
  const r = D.onoff[document.getElementById("osel").value];
  const keys = Object.keys(r.on).filter(k => k !== "경기수");

  document.getElementById("obody").innerHTML = `
    <div class="stats">
      <div class="stat"><b>${r.on.경기수}</b><span>출전 경기</span></div>
      <div class="stat"><b>${r.off.경기수}</b><span>결장 경기</span></div>
    </div>
    <div class="chartbox"><canvas id="ochart"></canvas></div>
    <table><thead><tr><th>지표</th><th>출전</th><th>결장</th><th>차이</th></tr></thead>
    <tbody>${keys.map(k=>{
      const d = r.diff[k];
      // 실점과 상대 패스 성공률은 '낮을수록 좋은' 지표라 색을 뒤집습니다
      const lowerBetter = k.includes("실점") || k.includes("상대");
      const good = lowerBetter ? d < 0 : d > 0;
      return `<tr><td>${k}</td><td>${fmt(r.on[k])}</td><td>${fmt(r.off[k])}</td>
        <td class="${d===0?'':(good?'up':'down')}">${d>0?'+':''}${d}</td></tr>`;
    }).join("")}</tbody></table>
    ${r.warning ? `<div class="warn">${r.warning}</div>` : ""}
    <div class="warn">해석 주의: '출전'은 1분이라도 뛴 경기입니다. 상대 팀 전력, 홈/원정,
      다른 선수의 출전 여부가 함께 섞여 있습니다. 이 차이를 선수 한 명의 영향으로 단정할 수 없습니다.</div>`;

  // 차트에는 눈금 범위가 비슷한 지표만 담습니다.
  // (수비액션처럼 값이 30~40인 지표를 섞으면 나머지 막대가 납작해져서 안 보입니다)
  const keysChart = ["경기당 승점","경기당 득점","경기당 실점"];
  if(chartO) chartO.destroy();
  chartO = new Chart(document.getElementById("ochart"), {
    type:"bar",
    data:{ labels:keysChart, datasets:[
      {label:"출전", data:keysChart.map(k=>r.on[k]), backgroundColor:"#2ea3e8", borderRadius:4},
      {label:"결장", data:keysChart.map(k=>r.off[k]), backgroundColor:"#c9d6e4", borderRadius:4}]},
    options:{ maintainAspectRatio:false,
      plugins:{legend:{position:"bottom"}},
      scales:{y:{beginAtZero:true,grid:{color:"#eef2f6"}},x:{grid:{display:false}}}}
  });
}

// ── 탭 4: 용어 사전 ───────────────────────────────────────────
// 데이터 파일이 아니라 코드 안에 둔 이유:
//   글보다 자주 바뀌지 않고, 용어를 고칠 때 이 파일 한 곳만 보면 되기 때문입니다.
//   항목이 30개를 넘어가면 그때 data/glossary.js 로 분리하세요.
// "2026-09-29" → "2026년 9월 29일 기준 (27라운드 종료)"
function asOfLabel(meta) {
  const d = meta.as_of || meta.generated_at;
  const [y, m, day] = d.split("-").map(Number);
  const note = meta.as_of_note ? ` (${meta.as_of_note})` : "";
  return `${y}년 ${m}월 ${day}일 기준${note}`;
}

// 백과 예시 숫자: 순위표(standings.js)에서 읽어 옵니다. 매주 손으로 고치지 않아도 되게 하려는 장치입니다.
// 데이터가 없으면 null 이고, 각 예시는 아래의 고정 문장(fallback)을 그대로 씁니다.
const GX = (() => {
  const S = window.KFL_STANDINGS;
  if(!S || !S.teams || !S.reg || !S.race) return null;
  const me = S.teams.find(t => t.team === S.meta.team);
  if(!me) return null;
  const top = [...S.teams].sort((a, b) => b.시그마 - a.시그마)[0];   // 평균선 위로 가장 멀리 벗어난 팀
  const ppg = me.승점 / me.경기수;
  return {
    me, top, ppg3: ppg.toFixed(3), left: S.race.잔여경기,
    est: (me.승점 + ppg * S.race.잔여경기).toFixed(1),
    gdpg: (me.득실차 / me.경기수).toFixed(2),
    a: S.reg.intercept.toFixed(4), b: S.reg.slope.toFixed(4),
    r2: S.reg.r2.toFixed(2), r2pct: Math.round(S.reg.r2 * 100),
    sd: S.reg.resid_sd.toFixed(4), topR: top.잔차.toFixed(3),
    sg: (v) => (v >= 0 ? "+" : "-") + Math.abs(v).toFixed(2)
  };
})();

const GLOSSARY = [
  {
    cat: "데이터", t: "PPG (경기당 승점)", en: "Points Per Game",
    easy: "10경기를 뛴 학생과 3경기만 뛴 학생의 '총점'을 그냥 비교하면 불공평하죠? 축구도 마찬가지입니다. 26경기를 치른 대구FC와 20경기만 치른 팀의 승점을 그대로 비교하면 경기를 더 뛴 팀이 유리해 보입니다. PPG는 '한 경기당 평균 몇 점을 땄나'로 바꿔서 공정하게 비교하는 값입니다.",
    def: "총 승점을 치른 경기 수로 나눈 값입니다.",
    why: "팀마다 소화한 경기 수가 다를 때, 총 승점을 그대로 비교하면 경기를 더 치른 팀이 유리해 보입니다. 경기 수를 걷어내고 같은 잣대로 비교하려고 씁니다.",
    ex: GX ? `${GX.me.team} ${GX.me.승점}점 ÷ ${GX.me.경기수}경기 = ${GX.ppg3} PPG` : "대구FC 46점 ÷ 26경기 = 1.769 PPG",
    care: "경기 수가 적을수록 값이 요동칩니다. 5경기만 치른 팀의 PPG는 신뢰하기 어렵습니다.",
    where: "순위 분석 탭 ①②"
  },
  {
    cat: "데이터", t: "득실차", en: "Goal Difference (GD)",
    easy: "권투에서 판정승과 KO승은 똑같이 '1승'이지만 내용은 다르죠. 축구도 1-0으로 이긴 팀과 5-0으로 이긴 팀은 승점이 똑같이 3점입니다. 득실차는 그 '얼마나 압도적으로 이기고 졌는지'를 숫자로 남겨서, 승점만으로는 안 보이는 팀의 진짜 힘을 가늠하게 해 줍니다.",
    def: "득점에서 실점을 뺀 값입니다. 경기당 득실차는 이것을 다시 경기 수로 나눈 값입니다.",
    why: "승점은 이겼는지 졌는지만 알려주지만, 득실차는 얼마나 차이 나게 이기고 졌는지를 담습니다. 팀 전력을 재는 지표로 승점보다 덜 흔들린다고 알려져 있습니다.",
    ex: GX ? `${GX.me.team} ${GX.me.득실차 >= 0 ? "+" : ""}${GX.me.득실차} ÷ ${GX.me.경기수}경기 = 경기당 ${GX.me.득실차 >= 0 ? "+" : ""}${GX.gdpg}` : "대구FC +13 ÷ 26경기 = 경기당 +0.50",
    care: "한 경기 대패가 값을 크게 흔듭니다.",
    where: "순위 분석 탭 ①②"
  },
  {
    cat: "데이터", t: "회귀분석", en: "Regression",
    easy: "'슈팅을 많이 때리는 팀이 대체로 골도 많이 넣는다' 같은 경향을 직선 하나로 요약하는 방법입니다. 이 사이트에서는 '득실차가 이 정도면 승점은 보통 이 정도'라는 기준선을 그어서, 각 팀이 그 선보다 승점을 더 땄는지 덜 땄는지를 비교합니다.",
    def: "두 숫자 사이에 어떤 직선 관계가 있는지 찾아내는 방법입니다.",
    why: "여기서는 '경기당 득실차가 이만큼이면 승점은 대개 이 정도'라는 기준선을 긋기 위해 썼습니다. 그 선에서 얼마나 벗어났는지를 보면 각 팀이 성적을 더 냈는지 덜 냈는지 알 수 있습니다.",
    ex: GX ? `PPG = ${GX.a} + ${GX.b} × 경기당 득실차` : "PPG = 1.3378 + 0.7609 × 경기당 득실차",
    care: "관계가 있다는 것이지 원인이라는 뜻은 아닙니다. 득실차가 좋아서 승점이 높은 것인지, 강팀이라 둘 다 높은 것인지 이 식만으로는 구분할 수 없습니다.",
    where: "순위 분석 탭 ①"
  },
  {
    cat: "데이터", t: "회귀식", en: "Regression Equation",
    easy: "그 기준선을 수식으로 적어 둔 것입니다. 축구화 사이즈로 발 길이를 어림잡는 표처럼, 득실차 숫자를 넣으면 '이 정도 득실차인 팀은 보통 승점이 이만큼'이라는 예상치가 바로 계산되어 나옵니다.",
    def: "회귀분석으로 얻은 직선의 수식입니다. 기울기와 시작점으로 이루어집니다.",
    why: "숫자를 넣으면 '기대되는 값'이 바로 나옵니다.",
    ex: GX ? `경기당 득실차가 0인 팀의 기대 PPG = ${GX.a}. 득실차가 경기당 1점씩 앞서면 PPG가 ${GX.b} 올라갑니다.` : "경기당 득실차가 0인 팀의 기대 PPG = 1.3378. 득실차가 경기당 1점씩 앞서면 PPG가 0.7609 올라갑니다.",
    care: "데이터 범위 밖에서는 믿을 수 없습니다. 경기당 득실차 +5 같은 값을 넣어도 숫자는 나오지만 의미가 없습니다.",
    where: "순위 분석 탭 ①"
  },
  {
    cat: "데이터", t: "R² (결정계수)", en: "R-squared · 설명력",
    easy: "골키퍼가 슈팅 방향을 얼마나 잘 읽는지 점수로 매긴다고 생각해 보세요. R²는 그은 기준선이 실제 순위를 얼마나 잘 '읽어 맞히는지'를 0~1로 매긴 점수입니다. 1에 가까우면 득실차만 봐도 승점이 거의 설명되고, 0에 가까우면 득실차와 승점이 따로 놉니다.",
    def: "회귀선이 실제 데이터를 얼마나 잘 설명하는지를 0~1로 나타낸 값입니다.",
    why: "선을 그었는데 데이터가 선 근처에 몰려 있으면 1에 가깝고, 흩어져 있으면 0에 가깝습니다. 이 선을 믿어도 되는지 판단하는 첫 번째 잣대입니다.",
    ex: GX ? `R² = ${GX.r2} → 승점 변동의 ${GX.r2pct}%를 득실차만으로 설명할 수 있다는 뜻입니다.` : "R² = 0.94 → 승점 변동의 94%를 득실차만으로 설명할 수 있다는 뜻입니다.",
    care: "R²가 높다고 인과관계가 있는 것은 아닙니다. 또 표본이 적으면 우연히 높게 나올 수 있습니다. 여기서는 17개 팀뿐입니다.",
    where: "순위 분석 탭 ① 요약 카드"
  },
  {
    cat: "데이터", t: "잔차", en: "Residual",
    easy: "이 선수는 이 정도 슈팅을 때리면 보통 이 정도 골을 넣는데, 이번 시즌엔 그보다 더 혹은 덜 넣었다 — 그 '더/덜'이 잔차입니다. 득실차로 예상되는 승점보다 실제로 더 벌었는지 덜 벌었는지를 숫자로 남긴 것입니다.",
    def: "실제 값에서 회귀선이 예측한 값을 뺀 차이입니다.",
    why: "'득실차만 보면 이 정도 승점이어야 하는데, 실제로는 더 벌었다/덜 벌었다'를 숫자로 만든 것입니다. 회귀분석에서 실제로 읽는 것은 선이 아니라 이 차이입니다.",
    ex: (GX && GX.top.잔차 > 0) ? `${GX.top.team} 잔차 +${GX.topR} PPG → 득실차로 예상되는 것보다 경기당 ${GX.topR}점을 더 벌었습니다. ${GX.top.경기수}경기면 약 +${GX.top.잔차_시즌환산.toFixed(1)}점입니다.` : "수원삼성 잔차 +0.204 PPG → 득실차로 예상되는 것보다 경기당 0.204점을 더 벌었습니다. 25경기면 약 +5.1점입니다.",
    care: "잔차가 크다고 '승부처에 강하다'고 말할 수 없습니다. 박빙 경기 결과가 우연히 한쪽으로 몰린 것일 수도 있습니다.",
    where: "순위 분석 탭 ①②"
  },
  {
    cat: "데이터", t: "σ (시그마, 표준편차)", en: "Standard Deviation",
    easy: "반 전체 시험 점수가 다들 고만고만한 반과, 1등과 꼴찌 차이가 아주 큰 반은 평균이 같아도 분위기가 다르죠. σ는 그 '흩어진 정도'를 재는 자입니다. 잔차가 +0.2였다고 해도, 이 자로 재봐야 그게 흔한 편차인지 아주 튀는 편차인지 알 수 있습니다.",
    def: "값들이 평균에서 평균적으로 얼마나 떨어져 있는지를 나타내는 숫자입니다.",
    why: "잔차가 +0.2라고 해도 그게 큰 값인지 알 수 없습니다. 흩어진 정도(σ)로 나누면 '보통보다 몇 배 벗어났는지'로 바꿔 읽을 수 있습니다.",
    ex: (GX && GX.top.잔차 > 0) ? `잔차 표준편차 σ = ${GX.sd} PPG. ${GX.top.team} 잔차 +${GX.topR} ÷ ${GX.sd} = ${GX.sg(GX.top.시그마)}σ` : "잔차 표준편차 σ = 0.1112 PPG. 수원삼성 잔차 +0.204 ÷ 0.1112 = +1.83σ",
    care: "σ 자체는 좋고 나쁨이 아니라 '흩어진 정도'일 뿐입니다. 표본이 적으면 σ도 부정확합니다.",
    where: "순위 분석 탭 ① 요약 카드, 회색 띠"
  },
  {
    cat: "데이터", t: "1.5σ 기준", en: "",
    easy: "심판이 오프사이드를 애매한 상황마다 다 잡지 않고 '명백할 때만' 잡는 것과 비슷합니다. 표본(17팀)이 적어서 작은 차이는 우연과 구분이 안 되니, 이 사이트는 '1.5σ 이상 벗어난 팀만' 특별하다고 해석하기로 미리 정해 뒀습니다.",
    def: "이 사이트에서 '유의미하다'고 부르는 선입니다. 잔차가 1.5σ를 넘은 팀만 해석 대상으로 삼습니다.",
    why: "표본이 17팀뿐이라 작은 차이는 우연과 구분되지 않습니다. 선을 미리 그어 두면 '숫자가 조금 높으니 뭔가 있다'는 식의 과잉 해석을 막을 수 있습니다.",
    ex: (GX && Math.abs(GX.me.시그마) < 1.5) ? `${GX.me.team} ${GX.sg(GX.me.시그마)}σ → 기준 미달이므로 해석하지 않습니다. 특별할 것이 없다는 뜻입니다.` : "대구FC +0.46σ → 기준 미달이므로 해석하지 않습니다. 특별할 것이 없다는 뜻입니다.",
    care: "1.5σ는 절대 기준이 아니라 이 프로젝트가 스스로 정한 선입니다. 통계학 교과서의 관례(보통 2σ)보다 느슨합니다. 표본이 늘면 더 엄격하게 잡아야 합니다.",
    where: "순위 분석 탭 ① 회색 띠 바깥 팀"
  },
  {
    cat: "데이터", t: "2로빈", en: "Double Round-robin",
    easy: "조기축구 리그에서 모든 팀과 '홈'에서 한 번, '원정'에서 한 번씩 붙는 것과 같습니다. 총 두 번씩 만나기 때문에 일정이 한쪽 팀에만 유리하게 짜이는 걸 막아 줍니다.",
    def: "모든 팀이 서로 홈과 원정에서 한 번씩, 총 두 번 맞붙는 방식입니다.",
    why: "일정의 유불리를 줄이는 기본 방식입니다. 총 경기 수를 계산하는 근거가 됩니다.",
    ex: "K리그2 2026은 17팀 2로빈입니다. 팀이 홀수라 매 라운드 한 팀이 쉬고, 34라운드 동안 팀당 32경기를 치릅니다.",
    care: "K리그1처럼 시즌 중간에 그룹을 나누는 스플릿 방식은 2로빈이 아닙니다. 리그마다 다릅니다.",
    where: "연재 1편 1장"
  },
  {
    cat: "축구", t: "오프사이드", en: "Offside",
    easy: "공보다 먼저 가서 골대 앞에 서 있다가 받아먹는 것을 막는 규칙입니다. 동네 축구에서 \'골대 앞에 서 있기 없기\'라고 정하는 것과 같습니다.",
    def: "동료가 공을 차는 순간, 공을 받을 선수가 상대 진영에서 뒤에서 두 번째 상대 선수(보통 마지막 수비수)보다 골대에 더 가깝게 있으면 반칙입니다.",
    why: "공격수가 상대 골대 앞에만 머물면 경기가 성립하지 않습니다. 수비진이 라인을 올려 공간을 좁히는 전술도 이 규칙 덕분에 성립합니다.",
    ex: "패스를 차는 순간 기준입니다. 공을 받는 순간이 아니라서, 뛰어들어가면서 받는 것은 반칙이 아닙니다.",
    care: "자기 진영에 있거나, 골킥·스로인·코너킥에서는 적용되지 않습니다. 그 위치에 있었더라도 플레이에 관여하지 않았다면 반칙이 아닙니다.",
    img: { src: "img/offside.svg", alt: "패스를 차는 순간 받는 선수가 뒤에서 두 번째 수비수 선보다 골대 쪽에 있으면 오프사이드이고, 선 뒤에 있다가 차는 순간 이후 뛰어들어가 받으면 반칙이 아님을 보여 주는 그림" },
    where: "축구 규칙"
  },
  {
    cat: "축구", t: "승점", en: "Points",
    easy: "매 경기 받는 점수입니다. 이기면 3점, 비기면 1점, 지면 0점. 이 점수를 시즌 내내 더해서 순위를 매깁니다.",
    def: "승·3점, 무·1점, 패·0점으로 누적한 점수입니다.",
    why: "승부만으로 줄을 세우기 위한 가장 기본이 되는 숫자입니다. 승리에 3점을 주는 것은 비기기보다 이기려고 달려들도록 유도하는 장치입니다.",
    ex: "10승 8무 8패 → 10×3 + 8×1 = 38점",
    care: "승점이 같을 때 순위를 가리는 순서는 리그마다 다릅니다. 아래 '승점이 같을 때 순위' 항목을 보세요.",
    where: "한눈에 탭, 순위 분석 탭"
  },
  {
    cat: "축구", t: "승점이 같을 때 순위", en: "Tiebreakers",
    easy: "시험 총점이 같은 두 학생의 등수를 정할 때, '수학 점수가 높은 쪽'처럼 미리 정한 기준을 차례로 보죠. K리그2도 승점이 같으면 정해진 기준을 하나씩 비교해서, 먼저 차이가 나는 기준으로 순위를 정합니다.",
    def: "K리그2 2026 정규 라운드(1~34R) 순위는 승점 → 다득점 → 득실차 → 다승 → 승자승 → 벌점 → 추첨 순으로 정합니다. (출처: 하나은행 K리그2 2026 대회요강 제30조)",
    why: "다득점은 넣은 골의 합계입니다. 잉글랜드 프리미어리그처럼 득실차를 먼저 보는 리그가 많지만, K리그는 다득점을 먼저 봅니다. 그래서 실점이 많아도 골을 많이 넣은 팀이 동률에서 앞설 수 있습니다.",
    ex: "두 팀이 승점 61점으로 같고 A팀 55골, B팀 52골이면 득실차와 상관없이 A팀이 위입니다.",
    care: "벌점은 경고·퇴장 등으로 쌓이는 팀 벌점입니다. 이 사이트의 승격 확률 계산은 득실차만 쓰고 다득점은 반영하지 않습니다.",
    where: "순위 분석 탭(2위 추격 표), 승격 확률 탭"
  },
  {
    cat: "축구", t: "승격과 강등", en: "Promotion / Relegation",
    easy: "리그가 위아래로 이어져 있어서, 성적이 좋으면 위 리그로 올라가고 나쁘면 내려갑니다. 대구FC는 지금 2부인 K리그2에 있고, 1부인 K리그1로 올라가는 것이 시즌 목표입니다.",
    def: "시즌 성적에 따라 상위 리그와 하위 리그를 오가는 제도입니다.",
    why: "순위 싸움이 시즌 끝까지 의미를 갖게 만듭니다. 중위권 팀도 올라갈 수 있고 밀릴 수 있습니다.",
    ex: "K리그2 2026은 17팀입니다. 1~2위는 자동 승격, 3~6위는 승격 플레이오프로 갑니다.",
    care: "승격 정원과 방식은 연도별로 바뀝니다. 연도가 다른 글을 그대로 믿으면 안 됩니다.",
    where: "한눈에 탭"
  },
  {
    cat: "축구", t: "승격 플레이오프", en: "Promotion Play-off",
    easy: "자동 승격을 놓친 팀들에게 주는 패자부활전입니다. 정규리그 3~6위가 단판승부로 붙어 올라갈 한 자리를 다툽니다.",
    def: "정규리그 상위권 팀들이 승격 티켓을 놓고 치르는 추가 경기입니다.",
    why: "자동 승격이 멀어진 팀도 마지막까지 동기를 갖게 합니다.",
    ex: GX ? `${GX.me.team}는 현재 ${GX.me.총점순위}위입니다. 3~6위에 들면 플레이오프권 안에 있는 것입니다.` : "대구FC는 현재 4위로 이미 플레이오프권(3~6위) 안에 있습니다.",
    care: "단판승부라 정규리그 순위가 높아도 한 경기에 끝날 수 있습니다. 순위가 곧바로 승격으로 이어지지 않습니다.",
    where: "한눈에 탭, 순위 분석 탭 ③"
  },
  {
    cat: "축구", t: "클린시트", en: "Clean Sheet",
    easy: "한 경기를 무실점으로 마치는 것입니다. 수비진과 골키퍼의 성적표 같은 숫자입니다.",
    def: "실점 없이 경기를 끝낸 것을 말합니다.",
    why: "실점을 0으로 막으면 최소 승점 1점은 확보됩니다. 수비 안정성을 대략 보여 주는 지표입니다.",
    ex: "26경기에서 10번 무실점 → 클린시트 10회",
    care: "약한 상대를 많이 만났는지까지는 담지 못합니다. 상대 수준을 같이 보지 않으면 과대평가됩니다.",
    where: "축구 기록"
  },
  {
    cat: "축구", t: "어시스트와 키패스", en: "Assist / Key Pass",
    easy: "골로 연결된 마지막 패스가 어시스트, 골은 안 됐지만 슈팅까지 이어진 패스가 키패스입니다.",
    def: "어시스트는 득점으로 이어진 패스, 키패스는 슈팅으로 이어진 패스입니다.",
    why: "기회를 만드는 선수를 찾기 위해 봅니다. 골은 동료의 마무리 능력에 좌우되므로, 키패스가 더 꾸준한 지표로 알려져 있습니다.",
    ex: "키패스 40회, 어시스트 3개 → 기회는 꽤 만들었지만 마무리가 적었다는 뜻입니다.",
    care: "어시스트는 동료가 넣어야 생깁니다. 적다고 패스가 나쁘았다고 말할 수 없습니다.",
    where: "선수 탭"
  },
  {
    cat: "축구", t: "점유율", en: "Possession",
    easy: "공을 우리 팀이 가지고 있었던 시간의 비율입니다. 높다고 잘한 것도, 낮다고 못한 것도 아닙니다.",
    def: "경기 중 한 팀이 공을 소유한 시간(또는 패스 수)의 비율입니다.",
    why: "팀이 경기를 어떻게 풀어가려 했는지 보여 줍니다. 높은 점유율과 역습 위주는 둘 다 하나의 전략입니다.",
    ex: "점유율 62%인데 슈팅이 6개라면, 공은 많이 돌렸지만 위협은 적었다는 신호입니다.",
    care: "점유율과 승리의 관계는 약합니다. 이기고 있는 팀이 공을 내주는 경우도 흔합니다.",
    where: "팀 비교 탭"
  },
  {
    cat: "데이터", t: "패스 방향 (전방·횡·백)", en: "Forward / Lateral / Backward Pass",
    easy: "공을 찬 선수가 상대 골대 쪽을 보고 있다고 생각하면, 앞쪽으로 보낸 패스가 전방 패스, 옆으로 보낸 패스가 횡패스, 뒤로 보낸 패스가 백패스입니다. 거리는 보지 않고 방향(각도)만 봅니다.",
    def: "K리그 데이터포털 부가기록(공급: Bepro11) 기준으로, 정면에서 좌우 60° 안(모두 120°)이면 전방 패스, 그 양옆 60°씩이 횡패스, 나머지 뒤쪽 120°가 백패스입니다.",
    img: { src: "img/pass_direction.png", alt: "공을 찬 선수를 중심으로 정면 120°는 전방 패스, 양옆 60°씩은 횡패스, 뒤쪽 120°는 백패스로 나눈 그림" },
    why: "팀이 공을 앞으로 보내려 했는지, 옆으로 돌리며 틈을 찾았는지 대략 가늠할 수 있습니다.",
    ex: "3월 22일 부산전 대구의 성공 패스 중 횡패스 47%, 전방 패스 31% (시즌 평균 41%, 35%)",
    care: "거리 조건이 없어 자기 진영에서 짧게 앞으로 준 패스도 전방 패스입니다. 전방 패스 비중이 높다고 위협적인 공격을 했다는 뜻은 아닙니다.",
    where: "[분석 #3] 점유율 글"
  },
  {
    cat: "축구", t: "압박 (프레싱)", en: "Pressing",
    easy: "공을 가진 상대를 여러 명이 빨리 달라붙어 괴롭히는 수비 방식입니다. 높은 위치에서 뺏으면 골대에 가까워집니다.",
    def: "상대가 공을 편하게 다루지 못하도록 압박해 소유권을 뺏으려는 수비 행동입니다.",
    why: "상대 진영에서 공을 뺏으면 수비가 정리되기 전에 공격할 수 있어 기대 득점이 큽니다.",
    ex: "앞에서 강하게 걸면 전방압박, 내려서 진을 갖추면 로우 블록이라고 부릅니다.",
    care: "앞에서 걸면 뒤쪽 공간이 비기 쉽습니다. 체력 소모도 커서 90분 내내 유지하기 어렵습니다.",
    where: "기술 스펙 (PPDA)"
  },
  {
    cat: "축구", t: "세트피스", en: "Set Piece",
    easy: "공이 멈춰 있는 상황에서 다시 시작하는 장면입니다. 코너킥·프리킥·페널티가 여기에 들어갑니다.",
    def: "플레이가 중단된 뒤 정해진 위치에서 재개되는 공격 상황입니다.",
    why: "유일하게 사전에 연습한 그대로 재현할 수 있는 장면이라, 전력 차가 나는 팀끼리의 경기에서 승부처가 됩니다.",
    ex: "리그 전체 득점의 약 1/4이 세트피스에서 나온다고 알려져 있습니다. [미검증]",
    care: "세트피스 득점은 횟수가 적어 한두 경기 결과로 비율이 크게 흔들립니다.",
    where: "축구 전술"
  },
  {
    cat: "축구", t: "VAR", en: "Video Assistant Referee",
    easy: "영상으로 판정을 다시 보는 제도입니다. 모든 장면이 아니라 경기를 바로 바꿀 만한 장면만 봅니다.",
    def: "득점, 페널티, 직접 퇴장(레드카드), 선수 오인 네 가지 상황을 영상으로 검토하는 제도입니다.",
    why: "경기 결과를 바꾸는 명백한 오심을 줄이기 위해 도입됐습니다.",
    ex: "골이 들어간 뒤에도 그 이전의 오프사이드를 되돌려 확인해 득점을 취소할 수 있습니다.",
    care: "\'명백한 오류\'일 때만 개입합니다. 애매한 판정은 그대로 유지됩니다.",
    where: "축구 규칙"
  },
  {
    cat: "축구", t: "홈과 원정", en: "Home / Away",
    easy: "자기 구장에서 하는 경기가 홈, 상대 구장으로 가서 하는 경기가 원정입니다. 보통 홈이 유리합니다.",
    def: "경기가 열리는 장소 기준의 구분입니다.",
    why: "응원, 이동 피로, 익숙한 경기장 때문에 성적 차가 생깁니다. 데이터 분석에서는 보정해야 할 대표적인 교란 변수입니다.",
    ex: "잔여 일정에 원정이 많으면 같은 상대라도 어려워집니다.",
    care: "홈 이점의 크기는 리그·시즌마다 다릅니다. 이 사이트는 아직 홈/원정을 분리해 보정하지 않습니다.",
    where: "순위 분석 탭"
  },
  {
    cat: "축구", t: "승점 6점짜리 경기", en: "Six-pointer",
    easy: "순위 경쟁 중인 두 팀이 직접 맞붙는 경기를 부르는 말입니다. 이기면 내가 3점을 얻고, 경쟁 상대는 그 경기에서 승점을 못 얻으니 한 경기로 두 팀 사이가 크게 벌어지거나 좁혀진다는 뜻입니다.",
    def: "승점 경쟁 중인 팀끼리의 맞대결을 가리키는 관용 표현입니다. 실제로 6점을 주는 규칙은 없습니다.",
    why: "경쟁팀과의 승점 차를 한 경기로 가장 크게 바꿀 수 있는 경기입니다. 그래서 남은 일정에 이런 경기가 몇 개인지가 추격 가능성을 가늠하는 단서가 됩니다.",
    ex: "A팀 50점, B팀 47점일 때 B가 A를 직접 이기면 50 대 50이 됩니다. B가 다른 팀을 이기면, 같은 라운드에 A도 이길 경우 여전히 3점 차입니다.",
    care: "비기면 두 팀 모두 1점씩이라 차이는 그대로입니다. 몇 위까지를 '경쟁팀'으로 보는지는 말하는 사람마다 다릅니다. 연재 1편은 2위 싸움을 기준으로 썼습니다.",
    where: "연재 1편 4장, 순위 분석 탭 ④"
  },
  {
    cat: "데이터", t: "페이스 (최종 승점 추정)", en: "Points Pace",
    easy: "마라톤 중간 기록으로 '이 속도면 몇 시간에 들어온다'를 어림하는 것과 같습니다. 지금까지의 경기당 승점을 남은 경기에도 그대로 곱해 최종 승점을 짐작합니다.",
    def: "최종 승점 추정 = 현재 승점 + 경기당 승점(PPG) × 남은 경기 수",
    why: "경기 수가 다른 팀들의 '도착 지점'을 같은 조건으로 나란히 놓을 수 있습니다. 추격 계산에서 경쟁팀이 대략 어디까지 갈지 기준선을 잡을 때 씁니다.",
    ex: GX ? `승점 ${GX.me.승점}점, 경기당 ${GX.ppg3}점, 남은 ${GX.left}경기 → ${GX.me.승점} + ${GX.ppg3} × ${GX.left} ≈ ${GX.est}점` : "승점 46점, 경기당 1.769점, 남은 6경기 → 46 + 1.769 × 6 ≈ 56.6점",
    care: "남은 상대의 강약, 홈/원정, 부상 같은 변화를 전혀 반영하지 않습니다. 확률이 아니라 '지금 속도 그대로라면'의 기준선일 뿐입니다.",
    where: "연재 1편 4장, 순위 분석 탭 ③"
  }
];

function esc(s){
  return String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
}

let GCAT = "all";      // 백과 카테고리: all | 축구 | 데이터
let GRENDER = null;    // 바깥(툴팁·주소창 해시)에서 목록을 다시 그리기 위한 통로

// 항목을 가리키는 짧은 이름. 블로그에서 #g=오프사이드 처럼 링크할 때 씁니다.
// 괄호 앞부분만 쓰고 공백을 없앱니다. "σ (시그마, 표준편차)" → "σ"
function termKey(g){ return g.t.split(" (")[0].replace(/\s+/g, ""); }

// 특정 용어를 펼친 채로 백과 탭을 엽니다.
function openTerm(key){
  switchTab("g");
  GCAT = "all";
  const cats = document.getElementById("gcats");
  if(cats) cats.querySelectorAll(".gcat").forEach(x => x.classList.toggle("on", x.dataset.c === "all"));
  const q = document.getElementById("gq");
  if(q) q.value = "";
  if(GRENDER) GRENDER("");
  const el = document.getElementById("g-" + encodeURIComponent(key));
  if(!el) return;
  el.classList.add("open");
  const head = el.querySelector(".ghead");
  if(head) head.setAttribute("aria-expanded", "true");
  el.scrollIntoView({behavior:"smooth", block:"center"});
  // 주소창에도 남겨서 링크를 그대로 복사할 수 있게 합니다.
  history.replaceState(null, "", "#g=" + encodeURIComponent(key));
}

function buildGlossary(){
  const list  = document.getElementById("glist");
  const count = document.getElementById("gcount");
  const q     = document.getElementById("gq");
  if(!list) return;

  function render(keyword){
    // 검색어를 소문자로 맞춰 비교합니다. 'R2' 로 쳐도 'R²' 항목이 걸리도록
    // 이름·정의·예시를 한 덩어리로 합쳐서 찾습니다.
    const k = (keyword || "").trim().toLowerCase();
    const hit = GLOSSARY.filter(g => {
      if(GCAT !== "all" && g.cat !== GCAT) return false;   // 카테고리 칩
      if(!k) return true;
      const hay = [g.t, g.en, g.def, g.why, g.ex, g.care, g.where]
                    .join(" ").toLowerCase()
                    .replace("²", "2").replace("σ", "시그마");
      return hay.includes(k.replace("²", "2"));
    });

    // '전체'의 기준은 지금 고른 카테고리 안의 개수입니다.
    const base = GLOSSARY.filter(g => GCAT === "all" || g.cat === GCAT).length;
    count.textContent = k ? `${hit.length}개 / ${base}개` : `${base}개`;

    if(!hit.length){
      list.innerHTML = `<p class="gempty">'${esc(keyword)}' 에 해당하는 용어가 없습니다.</p>`;
      return;
    }

    // 카드 전체가 아니라 제목 버튼만 클릭 가능하게 하고, 펼친 상태는
    // 검색어를 바꿀 때마다 다시 그려지므로 매번 접힌 채로 시작합니다.
    list.innerHTML = hit.map(g => `
      <div class="gitem" id="g-${encodeURIComponent(termKey(g))}" data-key="${esc(termKey(g))}">
        <button type="button" class="ghead" aria-expanded="false">
          <span class="gtitle">${esc(g.t)}${g.en ? `<small>${esc(g.en)}</small>` : ""}<span class="gtag">${g.cat === "축구" ? "축구 기본" : "데이터"}</span></span>
          <span class="gchev">▸</span>
        </button>
        <div class="gbody">
          <div class="geasy"><span class="glab">쉽게 말하면</span><span>${esc(g.easy)}</span></div>
          <p class="gdef">${esc(g.def)}</p>
          ${g.img ? `<figure class="gimg"><img src="${esc(g.img.src)}" alt="${esc(g.img.alt)}" loading="lazy"></figure>` : ""}
          <div class="grow"><span class="glab">왜 쓰나</span><span>${esc(g.why)}</span></div>
          <div class="gex">예) ${esc(g.ex)}</div>
          <div class="grow"><span class="glab">주의</span><span>${esc(g.care)}</span></div>
          <div class="gwhere">쓰인 곳: ${esc(g.where)}</div>
        </div>
      </div>`).join("");
  }

  // 검색 결과가 다시 그려져도(innerHTML 교체) 버튼은 매번 새로 생기므로,
  // 목록 컨테이너 하나에 위임해서 한 번만 걸어 둡니다.
  list.addEventListener("click", e => {
    const head = e.target.closest(".ghead");
    if(!head) return;
    const item = head.closest(".gitem");
    const open = item.classList.toggle("open");
    head.setAttribute("aria-expanded", open ? "true" : "false");
    if(open && item.dataset.key){
      history.replaceState(null, "", "#g=" + encodeURIComponent(item.dataset.key));
    }
  });

  GRENDER = render;
  q.addEventListener("input", () => render(q.value));

  // 카테고리 칩. 고른 칩만 .on 을 갖고, 검색어는 유지한 채 다시 그립니다.
  const cats = document.getElementById("gcats");
  if(cats){
    cats.addEventListener("click", e => {
      const b = e.target.closest(".gcat");
      if(!b) return;
      GCAT = b.dataset.c;
      cats.querySelectorAll(".gcat").forEach(x => x.classList.toggle("on", x === b));
      render(q.value);
    });
  }
  render("");

  // 주소에 #g=오프사이드 가 붙어 있으면 그 항목을 펼친 채로 시작합니다.
  // (블로그 글에서 특정 용어로 바로 보내기 위한 통로)
  const h = decodeURIComponent((location.hash || "").replace(/^#g=/, ""));
  if(h && location.hash.startsWith("#g=")) setTimeout(() => openTerm(h), 0);
}



// ── 탭: 승격 확률 (몬테카를로 시뮬레이션) ─────────────────────
// 왜 시뮬레이션인가:
//   "몇 점이면 2위" 같은 산술 계산(순위 분석 탭 ③)은 '가능/불가능'만 알려줍니다.
//   실제로 얼마나 그럴듯한지는 남은 경기를 여러 번 치러봐야 감이 옵니다.
// 대진:
//   data/fixtures.js (K리그 공식 일정표를 옮긴 것)가 있으면 실제 대진대로 치릅니다.
//   없으면 예전 방식(남은 경기 수만 알고 무작위로 짝짓기)으로 돌아갑니다.
//   → 일정 파일이 빠져도 화면이 깨지지 않게 하려는 안전장치입니다.
const SIM_N = 10000;         // 반복 횟수. 3,000회는 ±1~2%p 흔들려서 늘렸습니다(실제 일정이라 계산이 가벼움).
const LEAGUE_GPG = 1.25;     // 팀당 경기당 평균 득점(가정값)
const TOTAL_GAMES = 32;      // 17팀 2로빈 → 팀당 32경기

// 포아송 난수(Knuth). 평균 l 인 '골 수'를 뽑습니다.
function rpois(l){
  const L = Math.exp(-l);
  let k = 0, p = 1;
  do { k++; p *= Math.random(); } while(p > L);
  return k - 1;
}

// 순위표 기준일(as_of) '이후' 날짜의 경기만 남은 경기로 봅니다.
// 시뮬레이션과 ④ 표가 이 함수 하나를 같이 씁니다. 규칙이 한 곳에만 있어야
// 둘이 서로 다른 '남은 경기'를 세는 일이 생기지 않습니다.
// 덕분에 이미 치른 라운드를 fixtures.js 에서 지우지 않아도 됩니다.
function upcomingFixtures(){
  const F = window.KFL_FIXTURES, S = window.KFL_STANDINGS;
  if(!F || !F.fixtures) return [];
  const asOf = (S && S.meta && S.meta.as_of) || "";
  return F.fixtures.filter(f => f.date > asOf);
}

// 순위 분석 ④ 대구 남은 경기 표. 해석은 넣지 않고 경기 수(사실)만 요약합니다.
function renderRemaining(){
  const S = window.KFL_STANDINGS, body = document.getElementById("s4-body");
  if(!S || !body) return;
  const MY = S.meta.team;
  const rank = new Map(S.teams.map(t => [t.team, t.총점순위]));
  const games = upcomingFixtures().filter(f => f.home === MY || f.away === MY);
  const W = "일월화수목금토", tier = [0, 0, 0];   // 1~2위 / 3~6위 / 7위 이하
  body.innerHTML = games.map(f => {
    const [y, m, d] = f.date.split("-").map(Number);
    const home = f.home === MY, opp = home ? f.away : f.home, r = rank.get(opp);
    if(r != null) tier[r <= 2 ? 0 : r <= 6 ? 1 : 2]++;
    const top = r != null && r <= 6;   // 승격권 상대는 강조
    return `<tr${top ? ' class="mine"' : ""}><td>${f.round}R</td>` +
      `<td>${m}.${String(d).padStart(2, "0")} (${W[new Date(y, m - 1, d).getDay()]})${f.time ? `<br><small>${f.time}</small>` : ""}</td>` +
      `<td>${esc(opp)}</td><td>${home ? "홈" : "원정"}</td>` +
      `<td>${r == null ? "-" : top ? `<b>${r}위</b>` : r + "위"}</td></tr>`;
  }).join("");
  document.getElementById("s4-n").textContent = games.length;
  document.getElementById("s4-asof").textContent =
    `${asOfLabel(S.meta)} 순위와 K리그 공식 일정표입니다. 일정은 연맹 사정으로 바뀔 수 있습니다.`;
  document.getElementById("s4-sum").textContent = games.length
    ? `남은 상대(지금 순위 기준): 1~2위 ${tier[0]}경기 · 3~6위 ${tier[1]}경기 · 7위 이하 ${tier[2]}경기`
    : "남은 경기가 없습니다.";
}

// 실제 일정표를 [홈 번호, 원정 번호] 목록으로 바꿉니다. 한 번만 만들면 됩니다.
// 팀 이름이 순위표와 하나라도 안 맞으면 null → 무작위 방식으로 돌아갑니다.
function fixturePairs(base){
  const F = window.KFL_FIXTURES;
  if(!F || !F.fixtures || !F.fixtures.length) return null;
  const idx = new Map(base.map((b, i) => [b.team, i]));
  const pairs = [];
  for(const f of upcomingFixtures()){
    if(!idx.has(f.home) || !idx.has(f.away)){
      console.warn("[KFL] 일정의 팀 이름이 순위표와 다릅니다:", f.home, f.away);
      return null;
    }
    pairs.push([idx.get(f.home), idx.get(f.away)]);
  }
  // 남은 경기 수가 순위표와 다르면(일정이 오래된 경우) 쓰지 않습니다.
  const cnt = base.map(() => 0);
  pairs.forEach(([i, j]) => { cnt[i]++; cnt[j]++; });
  if(cnt.some((c, i) => c !== base[i].left)){
    console.warn("[KFL] 일정표의 남은 경기 수가 순위표와 달라 무작위 대진을 씁니다.");
    return null;
  }
  return pairs;
}

let FIXED_PAIRS = undefined;   // undefined = 아직 안 만듦, null = 일정 없음
let SIM_MODE = "random";       // 화면 안내 문구에 씁니다

// 이번 반복에서 치를 경기 목록을 돌려줍니다.
function pairsFor(base){
  if(FIXED_PAIRS === undefined){
    FIXED_PAIRS = fixturePairs(base);
    SIM_MODE = FIXED_PAIRS ? "fixtures" : "random";
  }
  if(FIXED_PAIRS) return FIXED_PAIRS;
  // 예전 방식: 남은 경기 수만큼 '출전권'을 만들어 섞은 뒤 둘씩 짝짓습니다.
  const slots = [];
  base.forEach((b, i) => { for(let k = 0; k < b.left; k++) slots.push(i); });
  for(let i = slots.length - 1; i > 0; i--){
    const j = (Math.random() * (i + 1)) | 0;
    [slots[i], slots[j]] = [slots[j], slots[i]];
  }
  const out = [];
  for(let a = 0; a + 1 < slots.length; a += 2){
    if(slots[a] !== slots[a + 1]) out.push([slots[a], slots[a + 1]]);  // 자기 자신과 짝이면 버림
  }
  return out;
}

function simulate(S){
  const base = S.teams.map(t => ({
    team: t.team,
    pts0: t.승점,
    gd0:  t.득실차,
    left: Math.max(0, TOTAL_GAMES - t.경기수),
    r:    t.경기당득실차                    // 전력 대용치
  }));
  const n = base.length;
  const cnt = base.map(() => ({p1:0, p2:0, p6:0, pts:0}));

  for(let s = 0; s < SIM_N; s++){
    const pts = base.map(b => b.pts0);
    const gd  = base.map(b => b.gd0);

    for(const [i, j] of pairsFor(base)){
      const d = base[i].r - base[j].r;
      const li = Math.min(5, Math.max(0.15, LEAGUE_GPG + d / 2));
      const lj = Math.min(5, Math.max(0.15, LEAGUE_GPG - d / 2));
      const gi = rpois(li), gj = rpois(lj);
      gd[i] += gi - gj; gd[j] += gj - gi;
      if(gi > gj){ pts[i] += 3; }
      else if(gi < gj){ pts[j] += 3; }
      else { pts[i] += 1; pts[j] += 1; }
    }

    // 승점 → 득실차 순으로 줄 세웁니다(다득점은 데이터가 없어 생략).
    const order = base.map((_, i) => i)
      .sort((x, y) => (pts[y] - pts[x]) || (gd[y] - gd[x]) || (Math.random() - .5));
    order.forEach((idx, rank) => {
      if(rank === 0) cnt[idx].p1++;
      if(rank <= 1) cnt[idx].p2++;
      if(rank <= 5) cnt[idx].p6++;
      cnt[idx].pts += pts[idx];
    });
  }

  return base.map((b, i) => ({
    team: b.team,
    left: b.left,
    pts0: b.pts0,
    p1: cnt[i].p1 / SIM_N * 100,
    p2: cnt[i].p2 / SIM_N * 100,
    p6: cnt[i].p6 / SIM_N * 100,
    avg: cnt[i].pts / SIM_N
  }));
}

let ODDS = null;

function buildOddsTab(){
  const S = window.KFL_STANDINGS;
  const selEl = document.getElementById("wsel");
  if(!selEl) return;
  if(!S){
    document.querySelector('nav button[data-t="w"]').style.display = "none";
    return;
  }

  const pct = v => v >= 99.5 ? "99.9%" : (v < 0.05 && v > 0 ? "0.1% 미만" : v.toFixed(1) + "%");
  // 확률(0~100)에 비례한 색 농도. 글자가 읽히도록 최대 45%까지만 칠합니다(선형, 과장 없음).
  const heat = v => `--a:${Math.round(Math.max(0, Math.min(100, v)) * 0.45)}%`;

  function draw(){
    const me = ODDS.find(o => o.team === selEl.value) || ODDS[0];
    document.getElementById("wodds").innerHTML = [
      ["우승 (1위)", me.p1],
      ["자동 승격 (2위 이내)", me.p2],
      ["승격 PO 진출 (6위 이내)", me.p6]
    ].map(([lab, v]) => `
      <div class="obox"><b>${pct(v)}</b><span>${lab}</span>
        <div class="obar"><i style="width:${Math.max(1, Math.min(100, v))}%"></i></div></div>`).join("");

    // 100칸 점 그림. 반올림한 값이라 0.4% 같은 작은 확률은 0칸이 됩니다(글로 따로 표시).
    const n2 = Math.round(me.p2);
    document.getElementById("wdots").innerHTML =
      Array.from({length:100}, (_, k) => `<i class="${k < n2 ? "on" : ""}"></i>`).join("");
    document.getElementById("wdotcap").innerHTML =
      `지금 기록이 이어진다면, 남은 시즌을 100번 치를 때 ${me.team}가 ` +
      `<b>2위 안(자동 승격)에 드는 건 약 ${n2 === 0 && me.p2 > 0 ? "1번 미만" : n2 + "번"}</b>입니다.`;

    // 일정 대조 날짜는 fixtures.js 의 meta 에서 읽습니다. 날짜를 HTML 에 직접 쓰지 않으므로
    // 일정을 공식 페이지와 다시 맞춘 뒤 fixtures.js 의 time_checked_at 만 고치면 됩니다.
    const fm = window.KFL_FIXTURES && window.KFL_FIXTURES.meta, chk = fm && (fm.time_checked_at || fm.checked_at);
    if(chk && document.getElementById("wchk")){
      const [, cm, cd] = chk.split("-").map(Number);
      document.getElementById("wchk").textContent = `10~11월 경기는 ${cm}월 ${cd}일 공식 페이지와 대조`;
    }

    if(SIM_MODE !== "fixtures"){
      document.getElementById("wmode").innerHTML =
        "<b>잔여 일정을 넣지 못했습니다.</b> 남은 경기를 무작위로 짝지어 돌립니다. 실제 대진과 다릅니다.";
    }

    document.getElementById("wnote").textContent =
      `${me.team} · 현재 승점 ${me.pts0} · 남은 경기 ${me.left}경기 · ` +
      `시뮬레이션 ${SIM_N.toLocaleString()}회 평균 최종 승점 ${me.avg.toFixed(1)}점`;

    const rows = [...ODDS].sort((a, b) => b.p2 - a.p2 || b.p6 - a.p6);
    document.getElementById("wtable").innerHTML = `
      <thead><tr><th>팀</th><th>승점</th><th>남은<br>경기</th>
        <th>우승</th><th>자동 승격<br><small>2위 이내</small></th>
        <th>PO 진출<br><small>6위 이내</small></th><th>예상 최종<br>승점</th></tr></thead>
      <tbody>${rows.map(o => `
        <tr class="${o.team === S.meta.team ? "mine" : ""}">
          <td>${teamBadge(o.team)}</td><td>${o.pts0}</td><td>${o.left}</td>
          <td><span class="pcell" style="${heat(o.p1)}">${pct(o.p1)}</span></td>
          <td><span class="pcell" style="${heat(o.p2)}">${pct(o.p2)}</span></td>
          <td><span class="pcell" style="${heat(o.p6)}">${pct(o.p6)}</span></td>
          <td>${o.avg.toFixed(1)}</td></tr>`).join("")}</tbody>`;
    syncTableHints();
  }

  selEl.innerHTML = [...S.teams]
    .sort((a, b) => a.총점순위 - b.총점순위)
    .map(t => `<option ${t.team === S.meta.team ? "selected" : ""}>${t.team}</option>`).join("");

  ODDS = simulate(S);
  draw();
  drawForecastLog();
  selEl.addEventListener("change", draw);
  document.getElementById("wrun").addEventListener("click", () => {
    ODDS = simulate(S);
    draw();
  });
}

// 예측 기록장: 위의 '다시 돌리기' 결과와 달리, 특정 날짜에 적어 두고 고치지 않는 예측입니다.
// 시즌이 끝나면 forecast_log.js 의 actual 에 실제 순위·승점을 채우면 표가 자동으로 비교해 줍니다.
function drawForecastLog(){
  const L = window.KFL_FORECAST_LOG;
  if(!L || !L.entries || !L.entries.length) return;
  const e = L.entries[L.entries.length - 1];          // 가장 최근 기록
  const A = e.actual;                                  // 시즌 전에는 null
  document.getElementById("wlogbox").hidden = false;
  document.getElementById("wloglead").innerHTML =
    `${e.as_of} 기록으로 ${e.made_at}에 적어 둔 예측입니다(${e.sims.toLocaleString()}회). ` +
    `이 숫자는 고치지 않습니다. ${A ? "오른쪽이 실제 결과입니다." : "시즌이 끝나면(11월 29일) 오른쪽 칸에 실제 결과를 채웁니다."}`;
  const rows = [...e.teams].sort((a, b) => b.avg_pts - a.avg_pts);
  const myTeam = window.KFL_STANDINGS ? window.KFL_STANDINGS.meta.team : "";
  document.getElementById("wlog").innerHTML = `
    <thead><tr><th>팀</th><th>자동 승격<br><small>2위 이내</small></th><th>PO 진출<br><small>6위 이내</small></th>
      <th>예상 최종<br>승점</th><th>실제<br>순위</th><th>실제<br>승점</th></tr></thead>
    <tbody>${rows.map(t => {
      const a = A && A[t.team];
      return `<tr class="${t.team === myTeam ? "mine" : ""}"><td>${teamBadge(t.team)}</td>
        <td>${t.p2}%</td><td>${t.p6}%</td><td>${t.avg_pts}</td>
        <td>${a ? a.rank + "위" : "-"}</td><td>${a ? a.pts : "-"}</td></tr>`;
    }).join("")}</tbody>`;
}

// ── 탭 홈: 한눈에 ─────────────────────────────────────────────
// 통계를 모르는 방문자가 가장 먼저 보는 화면입니다.
// 여기에는 '해석'을 쓰지 않습니다. 순위·승점·격차처럼 확인 가능한 사실만 둡니다.
function switchTab(k){
  const b = document.querySelector(`nav button[data-t="${k}"]`);
  if(b) b.click();
}

function buildHome(){
  const S = window.KFL_STANDINGS;
  const hero = document.getElementById("h-hero");
  if(!hero) return;

  if(!S){
    hero.innerHTML = `<p class="empty">순위 데이터가 아직 없습니다. python run.py standings 를 실행하세요.</p>`;
    return;
  }

  const teams = [...S.teams].sort((a, b) => a.총점순위 - b.총점순위);
  const me    = teams.find(t => t.team === S.meta.team);
  if(!me){ hero.innerHTML = `<p class="empty">${S.meta.team} 기록을 찾지 못했습니다.</p>`; return; }

  // 비교 대상: 자동 승격 경계(2위)입니다. 이미 2위 안이면 바로 아래 순위와 비교합니다.
  const target = me.총점순위 > 2 ? teams.find(t => t.총점순위 === 2)
                                 : teams.find(t => t.총점순위 === me.총점순위 + 1);
  const gapLabel = me.총점순위 > 2 ? "2위와의 승점 차" : `${me.총점순위 + 1}위와의 승점 차`;
  let gapNum = "-", gapTxt = "비교할 팀이 없습니다";
  if(target){
    const d = target.승점 - me.승점, a = Math.abs(d);
    gapNum = a + "점";
    gapTxt = me.총점순위 > 2
      ? `${target.team}(${target.승점}점)보다 ${d > 0 ? a + "점 적습니다" : (d === 0 ? "같습니다" : a + "점 많습니다")}. 2위 안에 들면 자동 승격입니다.`
      : `${target.team}(${target.승점}점)보다 ${d < 0 ? a + "점 많습니다" : "같은 점수입니다"}.`;
  }
  const left = (S.race && S.race.잔여경기 != null) ? S.race.잔여경기 : null;
  const zone = me.총점순위 <= 2 ? "자동 승격권(1~2위)" : (me.총점순위 <= 6 ? "승격 플레이오프권(3~6위)" : "승격 플레이오프권 밖");

  hero.innerHTML = `
    <div class="hbox"><em>현재 순위</em><b>${me.총점순위}위</b><span>${teams.length}팀 중 · ${zone}</span></div>
    <div class="hbox"><em>승점</em><b>${me.승점}점</b><span>${me.경기수}경기 동안 쌓은 점수입니다. 이기면 3점, 비기면 1점.</span></div>
    <div class="hbox"><em>${gapLabel}</em><b>${gapNum}</b><span>${gapTxt}</span></div>
    <div class="hbox"><em>남은 경기</em><b>${left != null ? left + "경기" : "-"}</b><span>시즌이 끝날 때까지 치를 경기 수입니다.</span></div>`;

  // 기준일: 공식 순위표와 대조한 날짜(as_of). 없으면 파일 생성일로 대신합니다.
  const asOfTxt = asOfLabel(S.meta);
  document.getElementById("h-asof").textContent =
    `${S.meta.season}시즌 · ${asOfTxt} · 출처: 한국프로축구연맹(K리그)`;
  const sAsOf = document.getElementById("s-asof");
  if (sAsOf) sAsOf.textContent = asOfTxt;

  // 위 6팀(승격 PO권까지) + 대구가 그 밖이면 대구 줄을 덧붙입니다.
  const rows = teams.filter(t => t.총점순위 <= 6);
  if(me.총점순위 > 6) rows.push(me);
  const zoneOf = r => r <= 2 ? `<span class="ox yes">자동 승격</span>`
                  : (r <= 6 ? `<span class="ox yes" style="background:rgba(46,163,232,.16);color:var(--blue)">승격 PO</span>`
                            : `<span class="ox no">밖</span>`);
  document.getElementById("h-table").innerHTML = `
    <thead><tr><th>순위</th><th>팀</th><th>경기</th><th>승점</th><th>득실차</th><th>구간</th></tr></thead>
    <tbody>${rows.map(t => `
      <tr class="${t.team === S.meta.team ? "mine" : ""}">
        <td>${t.총점순위}</td><td>${teamBadge(t.team)}</td><td>${t.경기수}</td>
        <td>${t.승점}</td><td>${t.득실차 > 0 ? "+" : ""}${t.득실차}</td>
        <td>${zoneOf(t.총점순위)}</td></tr>`).join("")}</tbody>`;

}

// ── 탭 홈: 카드 화면 (2026-10-01) ─────────────────────────────
// 앱처럼 '카드 한 장 = 질문 하나'로 나눕니다. 여기에도 해석은 쓰지 않고 확인 가능한 사실만 둡니다.
// 데이터: standings.js(공식 순위) · players.js 의 teams(팀 시즌 누적) · fixtures.js(일정)
//         recent.js(최근 5경기, python run.py recent) · series.js(연재 글)
function buildHomeCards(){
  const S = window.KFL_STANDINGS, D = window.KFL_DATA, F = window.KFL_FIXTURES;
  const R = window.KFL_RECENT, list = window.KFL_SERIES || [];
  const pan = document.getElementById("pan-h");
  if(!pan || !S) return;

  const esc = t => String(t == null ? "" : t)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const md = d => d.slice(5).replace("-", ".");                 // 2026-10-17 → 10.17
  const wd = d => "일월화수목금토"[new Date(d + "T00:00:00").getDay()];
  // 원형 배지만 (이름 없이). 색 규칙은 teamBadge 와 같습니다.
  const bdg = (name, size = "") => {
    const m = TEAM_META[name] || {c:"#888", i:String(name).slice(0, 2)};
    const ring = m.s ? `;box-shadow:0 0 0 2px var(--card),0 0 0 4px ${m.s}` : "";
    return `<span class="tbadge ${size}" style="background:${m.c};color:${m.t || "#fff"}${ring}">${m.i}</span>`;
  };

  const MY = S.meta.team;
  const st = [...S.teams].sort((a, b) => a.총점순위 - b.총점순위);
  const meS = st.find(t => t.team === MY);
  if(!meS) return;
  const rankOf = name => (st.find(t => t.team === name) || {}).총점순위;
  const recTeams = (D && D.meta && D.meta.team_is_real) ? D.teams : [];
  const meR = recTeams.find(t => t.team === MY);

  // ① 우리 팀 요약: 순위·승·무·패·승점
  document.getElementById("hm-me").innerHTML =
    `${bdg(MY, "lg")}<div><small>우리 팀 · ${esc(asOfLabel(S.meta))}</small><b>${esc(MY)}</b></div>`;
  document.getElementById("hm-strip").innerHTML =
    `<div class="rk"><b>${meS.총점순위}</b><span>위</span></div>` +
    (meS.승 != null ? `<div><b>${meS.승}</b><span>승</span></div><div><b>${meS.무}</b><span>무</span></div><div><b>${meS.패}</b><span>패</span></div>`
    : meR ? `<div><b>${meR.승}</b><span>승</span></div><div><b>${meR.무}</b><span>무</span></div><div><b>${meR.패}</b><span>패</span></div>`
         : `<div><b>${meS.경기수}</b><span>경기</span></div><div></div><div></div>`) +
    `<div><b>${meS.승점}</b><span>점</span></div>`;
  const zone = meS.총점순위 <= 2 ? "자동 승격권(1~2위)" : (meS.총점순위 <= 6 ? "승격 플레이오프권(3~6위)" : "승격 플레이오프권 밖");
  const second = st.find(t => t.총점순위 === 2);
  const left = (S.race && S.race.잔여경기 != null) ? S.race.잔여경기 : null;
  document.getElementById("hm-say").innerHTML =
    `${st.length}팀 중 <b>${meS.총점순위}위</b>, ${zone}입니다.` +
    (meS.총점순위 > 2 && second ? ` 자동 승격권인 2위 ${esc(second.team)}와 <b>승점 ${second.승점 - meS.승점}점</b> 차이입니다.` : "") +
    (left != null ? ` 남은 경기는 ${left}경기입니다.` : "");

  // 최근 5경기 (오래된 → 최근)
  const formEl = document.getElementById("hm-form");
  if(R && R.matches && R.matches.length){
    const cls = {"승":"w", "무":"d", "패":"l"};
    formEl.innerHTML = R.matches.map(m => `<div>${md(m.date)}<b>${esc(TEAM_META[m.opponent] ? TEAM_META[m.opponent].i : m.opponent)} ${m.gf}:${m.ga}</b><span class="hm-res ${cls[m.result]}">${m.result}</span></div>`).join("");
    document.getElementById("hm-form-asof").textContent = `${md(R.meta.as_of)}까지 · 왼쪽이 오래된 경기`;
  } else {
    formEl.parentNode.querySelector(".hm-sub").remove(); formEl.remove();
  }

  // ② 다음 경기: 일정표에서 대구의 첫 경기
  // 기록(recent.js)에 들어간 마지막 경기 '다음' 대구 경기를 고릅니다.
  // 그 경기 날짜가 오늘보다 지났는데 아직 기록이 없으면 '결과 반영 전'으로 표시합니다.
  // (경기 결과는 사람이 기록을 추가하고 python run.py recent 를 돌려야 바뀌기 때문)
  const lastDone = (R && R.meta && R.meta.as_of) || "";
  const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);   // 한국 시간 기준 날짜
  const nx = F && F.fixtures ? F.fixtures.find(f => (f.home === MY || f.away === MY) && f.date > lastDone) : null;
  const pending = nx && nx.date < today;
  document.getElementById("hm-next").innerHTML = nx ? `
    <div class="hm-mt"><span>${md(nx.date)} (${wd(nx.date)})${nx.time ? " " + nx.time : ""} · ${nx.round}라운드</span><span>${pending ? `<span class="hm-pill wait">결과 반영 전</span> ` : ""}<span class="hm-pill">${nx.home === MY ? "홈" : "원정"}</span></span></div>
    <div class="hm-vs">
      <div class="hm-side">${bdg(nx.home, "xl")}${esc(nx.home)}<em>${rankOf(nx.home)}위</em></div>
      <div class="hm-mid"><b>VS</b><small>홈 · 원정</small></div>
      <div class="hm-side">${bdg(nx.away, "xl")}${esc(nx.away)}<em>${rankOf(nx.away)}위</em></div>
    </div>` : `<p class="hm-note">남은 일정이 없습니다.</p>`;

  // 목록 한 줄: 순위 · 배지 · 팀(경기 수) · 값
  const row = (n, team, games, val, unit, zoneCls = "") => `
    <li class="${team === MY ? "mine" : ""}"><span class="n ${zoneCls}">${n}</span>${bdg(team)}
      <span class="nm"><b>${esc(team)}</b><small>${games}경기</small></span>
      <span class="v">${val}<span>${unit}</span></span></li>`;

  // ③ 승격 경쟁: 상위 6팀 (+ 대구가 밖이면 덧붙임)
  const drawRace = k => {
    const arr = [...st].sort((a, b) => k === "ppg" ? a.PPG순위 - b.PPG순위 : a.총점순위 - b.총점순위);
    const top = arr.slice(0, 6);
    let html = top.map((t, i) => row(i + 1, t.team, t.경기수,
      k === "ppg" ? t.PPG.toFixed(2) : t.승점, k === "ppg" ? "" : "점", i < 2 ? "auto" : "po")).join("");
    const mi = arr.findIndex(t => t.team === MY);
    if(mi >= 6) html += `<li class="gap">⋯</li>` + row(mi + 1, MY, meS.경기수, k === "ppg" ? meS.PPG.toFixed(2) : meS.승점, k === "ppg" ? "" : "점");
    document.getElementById("hm-race").innerHTML = html;
  };

  // ④ 팀 기록 TOP 5 (+ 대구가 5위 밖이면 덧붙임)
  const drawRec = k => {
    const recEl = document.getElementById("hm-rec");
    if(!recTeams.length){ recEl.closest(".hm-card").remove(); return; }
    const low = k === "경기당_실점";                 // 적을수록 좋은 지표
    const arr = [...recTeams].sort((a, b) => low ? a[k] - b[k] : b[k] - a[k]);
    const f = v => k === "득실차" ? (v > 0 ? "+" + v : v) : Number(v).toFixed(2);
    const unit = k === "득실차" ? "" : "골";
    let html = arr.slice(0, 5).map((t, i) => row(i + 1, t.team, t.경기수, f(t[k]), unit)).join("");
    const mi = arr.findIndex(t => t.team === MY);
    if(mi >= 5) html += `<li class="gap">⋯</li>` + row(mi + 1, MY, meR.경기수, f(meR[k]), unit);
    recEl.innerHTML = html;
    document.getElementById("hm-rec-note").textContent = low
      ? "실점은 적을수록 좋아서, 적은 팀이 위에 옵니다. 경기 수가 팀마다 달라 경기당 값으로 맞췄습니다."
      : (k === "득실차" ? "득실차는 넣은 골에서 내준 골을 뺀 값(누적)이라, 경기를 더 치른 팀이 조금 유리합니다."
                       : "경기 수가 팀마다 달라 경기당 값으로 맞췄습니다. 대구FC가 5위 밖이면 아래에 따로 보여 줍니다.");
  };

  pan.querySelectorAll(".hm-seg").forEach(seg => seg.addEventListener("click", e => {
    const b = e.target.closest("button"); if(!b) return;
    seg.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
    (seg.dataset.seg === "race" ? drawRace : drawRec)(b.dataset.k);
  }));
  drawRace("pts"); drawRec("경기당_득점");

  // ⑤ 연재 글: '준비 중' 제외, 최대 4개
  document.getElementById("hm-posts").innerHTML = list.filter(p => p.no !== "준비 중").slice(0, 4).map(p => {
    const pub = p.status === "published" && p.url;
    const when = pub ? `${md(p.date)} 발행` : `발행 전${p.date ? " · " + md(p.date) + " 예정" : ""}`;
    const inner = `<small>${when}</small><b>${esc(p.title)}</b><span>${esc(p.question)}</span>`;
    return pub ? `<a class="hm-post" href="${esc(p.url)}" target="_blank" rel="noopener">${inner}</a>`
               : `<div class="hm-post">${inner}</div>`;
  }).join("");

  // '→' 버튼: 해당 탭으로 이동
  pan.addEventListener("click", e => {
    const b = e.target.closest(".hm-more");
    if(b) switchTab(b.dataset.go);
  });
}

// ── 쉽게 / 자세히 ─────────────────────────────────────────────
// '쉽게'는 .adv 가 붙은 블록을 CSS로 통째로 숨깁니다(요소를 지우지 않음).
// 고른 값은 브라우저에 저장하지만, 저장이 막힌 환경(시크릿 창 등)에서도
// 화면은 정상 동작해야 하므로 try/catch 로 감쌉니다.
function initMode(){
  const sw = document.getElementById("modesw");
  if(!sw) return;
  const apply = m => {
    document.body.classList.toggle("easy", m === "easy");
    sw.querySelectorAll("button").forEach(b => b.classList.toggle("on", b.dataset.m === m));
    try{ localStorage.setItem("kfl_mode", m); }catch(e){}
  };
  let saved = "easy";
  try{ saved = localStorage.getItem("kfl_mode") || "easy"; }catch(e){}
  apply(saved);
  sw.addEventListener("click", e => {
    const b = e.target.closest("button");
    if(b) apply(b.dataset.m);
  });
}

// ── 본문 용어 → 점선 + 말풍선 ─────────────────────────────────
// 백과 탭으로 넘어가지 않아도 뜻을 볼 수 있게 합니다.
// '승점'처럼 너무 자주 나오는 말은 일부러 넣지 않았습니다(온통 점선이 되어 읽기 나빠짐).
const TERM_KEYS = {
  "PPG (경기당 승점)":      ["경기당 승점", "PPG"],
  "득실차":                 ["득실차"],
  "회귀분석":               ["회귀분석"],
  "회귀식":                 ["회귀식"],
  "R² (결정계수)":          ["R²", "결정계수"],
  "잔차":                   ["잔차"],
  "σ (시그마, 표준편차)":   ["표준편차", "σ"],
  "1.5σ 기준":              ["1.5σ"],
  "2로빈":                  ["2로빈"],
  "승격 플레이오프":        ["승격 플레이오프", "플레이오프"],
  "승격과 강등":            ["자동 승격"],
  "압박 (프레싱)":          ["압박"],
  "점유율":                 ["점유율"],
  "패스 방향 (전방·횡·백)": ["전방 패스", "횡패스", "백패스"],
  "오프사이드":             ["오프사이드"],
  "승점이 같을 때 순위":    ["다득점"]
};

function linkTerms(){
  const pairs = [];
  GLOSSARY.forEach(g => (TERM_KEYS[g.t] || []).forEach(k => pairs.push([k, g.t])));
  if(!pairs.length) return;
  // 긴 단어를 먼저 맞춰야 '경기당 승점'이 'PPG'보다 우선 잡힙니다.
  pairs.sort((a, b) => b[0].length - a[0].length);
  const re = new RegExp("(" +
    pairs.map(p => p[0].replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "g");

  // 백과 탭(#pan-g) 자체는 건드리지 않습니다. 설명 안에 또 점선이 생기면 지저분합니다.
  document.querySelectorAll(
    "#pan-h .hint, #pan-b .hint, #pan-i .hint, #pan-s .hint, #pan-s h3.sec, #pan-t .hint, #pan-o .hint, #pan-s .legend span"
  ).forEach(el => {
    const used = new Set();          // 한 문단에서 같은 단어는 한 번만 표시
    const nodes = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while(w.nextNode()) nodes.push(w.currentNode);

    nodes.forEach(node => {
      if(node.parentElement && node.parentElement.closest(".term")) return;
      const txt = node.nodeValue;
      re.lastIndex = 0;
      if(!re.test(txt)) return;

      const frag = document.createDocumentFragment();
      let last = 0, m;
      re.lastIndex = 0;
      while((m = re.exec(txt)) !== null){
        const key = m[0];
        if(used.has(key)) continue;
        used.add(key);
        frag.appendChild(document.createTextNode(txt.slice(last, m.index)));
        const sp = document.createElement("span");
        sp.className = "term";
        sp.dataset.g = pairs.find(p => p[0] === key)[1];
        sp.textContent = key;
        frag.appendChild(sp);
        last = m.index + key.length;
      }
      if(last === 0) return;         // 실제로 바꾼 것이 없으면 그대로 둡니다
      frag.appendChild(document.createTextNode(txt.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });
  });
}

function initTips(){
  const tip = document.createElement("div");
  tip.className = "tip";
  document.body.appendChild(tip);
  let cur = null;
  const hide = () => { tip.classList.remove("show"); cur = null; };

  // 모바일에서도 되도록 hover 가 아니라 click 으로 엽니다.
  document.addEventListener("click", e => {
    const t = e.target.closest(".term");
    if(!t){ if(!e.target.closest(".tip")) hide(); return; }
    if(cur === t){ hide(); return; }
    const g = GLOSSARY.find(x => x.t === t.dataset.g);
    if(!g) return;
    cur = t;
    tip.innerHTML = `<b>${esc(g.t)}</b>${esc(g.easy)}
      <div class="tipgo"><button type="button" class="golink" style="padding:6px 13px;font-size:.78rem"
        data-open="${esc(termKey(g))}">축구 백과에서 자세히 보기</button></div>`;
    tip.classList.add("show");
    const r = t.getBoundingClientRect();
    const maxL = window.scrollX + document.documentElement.clientWidth - tip.offsetWidth - 12;
    tip.style.top  = (r.bottom + window.scrollY + 6) + "px";
    tip.style.left = Math.max(12, Math.min(r.left + window.scrollX, maxL)) + "px";
  });
  // 말풍선 안의 버튼 → 백과 탭의 해당 항목으로 이동
  tip.addEventListener("click", e => {
    const b = e.target.closest("[data-open]");
    if(!b) return;
    hide();
    openTerm(b.dataset.open);
  });
  window.addEventListener("resize", hide);
  window.addEventListener("scroll", hide, {passive:true});
}

// init()은 buildGlossary()에서 GLOSSARY를 바로 참조하므로,
// GLOSSARY(const)가 선언된 다음, 파일 맨 끝에서 호출해야 합니다.
// (앞에서 호출하면 "Cannot access 'GLOSSARY' before initialization"로 죽고,
//  그 뒤에 있던 nav 버튼 클릭 바인딩까지 통째로 실행되지 않아 탭이 전부 안 눌립니다.)
init();
renderSeries();

// ── 홈: 연재 글 · 고친 기록 ───────────────────────────────────
// data/series.js 가 없거나 비어 있어도 나머지 화면은 그대로 동작하게 합니다.
// (함수 선언은 호이스팅되므로 위의 호출보다 뒤에 있어도 됩니다)
function renderSeries(){
  const esc = t => String(t == null ? "" : t)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const list = window.KFL_SERIES || [];
  const sEl = document.getElementById("h-series");

  if(sEl){
    sEl.innerHTML = list.map(x => {
      const pub = x.status === "published" && x.url;
      const when = pub ? `<span class="pill">${esc(x.date)} 발행</span>`
                       : `<span class="pill">발행 전${x.date ? " · " + esc(x.date) + " 예정" : ""}</span>`;
      const read = pub ? `<a class="golink sm" href="${esc(x.url)}" target="_blank" rel="noopener">블로그에서 읽기 →</a>` : "";
      const site = x.tab ? `<button type="button" class="golink sm" data-go="${esc(x.tab)}">사이트에서 보기</button>` : "";
      return `<li><span class="yr">${esc(x.no)}</span><span>
        <b>${esc(x.title)}</b><br><span class="q">${esc(x.question)}</span>
        <span class="meta">${when}${read}${site}</span></span></li>`;
    }).join("");
    sEl.addEventListener("click", e => {
      const b = e.target.closest("button.golink");
      if(b) switchTab(b.dataset.go);
    });
  }

  // 순위 분석 탭 맨 위 '연재 1편과 짝' 상자: 블로그 링크 + 섹션 이동
  const pair = document.getElementById("s-pair");
  const pairLink = document.getElementById("s-pair-link");
  if(pair && pairLink){
    const ep1 = list.find(x => x.no === "1편");
    const pub = ep1 && ep1.status === "published" && ep1.url;
    pairLink.innerHTML =
      (pub ? `<a class="golink sm" href="${esc(ep1.url)}" target="_blank" rel="noopener">블로그에서 1편 읽기 →</a>`
           : `<span class="pill">블로그 1편 발행 전</span>`) +
      `<button type="button" class="golink sm" data-go="b">연재 글 전체 보기</button>`;
    pair.addEventListener("click", e => {
      const j = e.target.closest("[data-jump]");
      if(j){
        const target = document.getElementById(j.dataset.jump);
        if(target) target.scrollIntoView({behavior: "smooth", block: "start"});
        return;
      }
      const g = e.target.closest("button[data-go]");
      if(g) switchTab(g.dataset.go);
    });
  }

}
