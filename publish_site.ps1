<#
  publish_site.ps1  -  사이트 수정분을 GitHub에 올리는 도우미 (add -> commit -> push)

  사용법 (C:\dev\kfootball-lab 폴더에서):
    .\publish_site.ps1 -Message "커밋 메시지" site/index.html site/data/series.js

  왜 만들었나:
    - 커밋 작성자 규칙(GH007 방지)을 매번 외우지 않기 위해
    - 'git add .' 로 작업 중 파일이나 원시 데이터가 섞여 올라가는 사고를 막기 위해
    - 올라갈 파일을 눈으로 확인하고 y 를 눌러야만 진행되게 하기 위해
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    # -Message 뒤에 적은 파일 이름들을 모두 받습니다.
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Files
)

# 이 스크립트가 있는 폴더(= 저장소 맨 위)에서 실행합니다.
Set-Location -Path $PSScriptRoot

$AuthorName = "daegu-football-lab"
$AuthorMail = "308194182+daegu-football-lab@users.noreply.github.com"

function Stop-Publish([string]$msg) {
    Write-Host "[중단] $msg" -ForegroundColor Red
    exit 1
}

# 1) 올리면 안 되는 파일 거르기 (약관 제4조, 원시 데이터 비공개 원칙)
foreach ($f in $Files) {
    $n = $f -replace '\\', '/'
    if ($n -match '(^|/)data/raw/' -or $n -match '\.csv$' -or $n -match '^posts/' -or $n -match '\.bak$') {
        Stop-Publish "공개하면 안 되는 파일입니다: $f"
    }
    if (-not (Test-Path -LiteralPath $f)) {
        Stop-Publish "파일이 없습니다: $f  (이름과 경로를 확인하세요)"
    }
}

# 2) 이미 커밋 대상에 담긴 다른 파일이 있으면 멈춤 (다른 작업이 섞이는 것 방지)
$already = @(git diff --cached --name-only)
if ($already.Count -gt 0) {
    Stop-Publish ("이미 커밋 대상에 담긴 파일이 있습니다: " + ($already -join ", ") + "`n   'git restore --staged <파일>' 로 뺀 뒤 다시 실행하세요.")
}

# 3) 지정한 파일만 담기
git add -- $Files
if ($LASTEXITCODE -ne 0) { Stop-Publish "git add 실패" }

$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Stop-Publish "바뀐 내용이 없습니다. 파일을 저장했는지, 이미 올렸는지 확인하세요."
}

# 4) 눈으로 확인
Write-Host ""
Write-Host "이번에 올라갈 파일:" -ForegroundColor Cyan
git diff --cached --stat
Write-Host "커밋 메시지: $Message"
$ans = Read-Host "올릴까요? (y 를 누르면 진행)"
if ($ans -ne "y") {
    git restore --staged -- $Files
    Stop-Publish "취소했습니다. 파일 내용은 그대로 남아 있습니다."
}

# 5) 커밋 (작성자 규칙 적용)
git -c "user.name=$AuthorName" -c "user.email=$AuthorMail" commit -m $Message
if ($LASTEXITCODE -ne 0) { Stop-Publish "커밋 실패" }

# 6) push
git push
if ($LASTEXITCODE -ne 0) {
    Stop-Publish "push 실패. 커밋은 저장됐습니다. 인터넷 연결을 확인하고 'git push' 만 다시 치세요."
}

$v = Get-Date -Format "MMddHHmm"
Write-Host ""
Write-Host "완료. 1~2분 뒤 확인: https://daegu-football-lab.github.io/kfootball-lab/site/?v=$v" -ForegroundColor Green
