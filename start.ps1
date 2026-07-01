# ============================================================================
# Woody – ett kommando på Windows (PowerShell): miljö + bygg + (Kodytek) + GUI.
#
#   powershell -ExecutionPolicy Bypass -File .\start.ps1
#   powershell -ExecutionPolicy Bypass -File .\start.ps1 -WithKodytek
#   powershell -ExecutionPolicy Bypass -File .\start.ps1 -WithKodytek -Train
#   powershell -ExecutionPolicy Bypass -File .\start.ps1 -Port 8080
#
# Öppna sedan webbgränssnittet på URL:en som skrivs ut (default http://localhost:8000).
# Kräver: Python 3.10+ och Node 18+ i PATH.
# ============================================================================
param(
  [switch]$WithKodytek,
  [switch]$Train,
  [switch]$Cuda,                # installera CUDA-torch (GPU) på Windows
  [string]$CudaUrl = "https://download.pytorch.org/whl/cu124",
  [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> 1/5  Python-miljö"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python saknas i PATH" }
if (-not (Test-Path ".venv")) { python -m venv .venv }
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $py -m pip install -q --upgrade pip
# På Windows ger 'pip install torch' CPU-bygget. För GPU (5090) installera
# CUDA-bygget först (övrigt blir då redan uppfyllt).
if ($Cuda -or $Train) {
  Write-Host "    installerar CUDA-torch ($CudaUrl) ... (för nyaste GPU kan en nyare cu-URL/nightly behövas)"
  & $py -m pip install -q torch --index-url $CudaUrl
}
Write-Host "    installerar Python-beroenden ..."
& $py -m pip install -q -r requirements.txt -r web/backend/requirements.txt
if ($Cuda -or $Train) {
  & $py -c "import torch; print('    torch', torch.__version__, '| CUDA tillgänglig:', torch.cuda.is_available())"
}

Write-Host "==> 2/5  Frontend (Vite-bygge)"
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm/node saknas – installera Node 18+" }
Push-Location web/frontend
npm install --no-audit --no-fund --silent
npm run build --silent
Pop-Location

$env:WOODY_KODYTEK_ROOT = ""
$env:WOODY_CKPT = "seg_unet.pt"

if ($WithKodytek) {
  Write-Host "==> 3/5  Kodytek-dataset (laddar ner + rastrerar – kan ta lång tid, flera GB)"
  if (-not (Test-Path "data\kodytek\images")) {
    & $py tools/download_kodytek.py --out data/kodytek_raw
    & $py -m src.kodytek --auto data/kodytek_raw --out data/kodytek
  } else {
    Write-Host "    data\kodytek finns redan – hoppar över nedladdning"
  }
  $env:WOODY_KODYTEK_ROOT = "data/kodytek"
} else {
  Write-Host "==> 3/5  Kodytek hoppas över (kör syntetisk data). Lägg till -WithKodytek för riktig data."
}

if ($Train) {
  Write-Host "==> 4/5  Tränar modellen på Kodytek (device=auto plockar GPU)"
  & $py -c "from src.config import SegConfig; from src.train import fit; fit(SegConfig.gpu_kodytek('data/kodytek'))"
  $env:WOODY_CKPT = "seg_kodytek.pt"
} else {
  Write-Host "==> 4/5  Träning hoppas över. Lägg till -Train för att träna på Kodytek."
}

Write-Host ""
Write-Host "==> 5/5  Startar server"
Write-Host "    Webbgränssnitt:  http://localhost:$Port"
Write-Host "    datakälla: $($env:WOODY_KODYTEK_ROOT)  |  modell: $($env:WOODY_CKPT)"
Write-Host "    (Ctrl+C för att stoppa)"
Write-Host ""
& $py -m uvicorn web.backend.app:app --host 0.0.0.0 --port $Port
