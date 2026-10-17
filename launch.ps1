$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$labPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $labPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed. Python 3.14 is the tested runtime.' }
}
& $labPython -c "import importlib.metadata as m; assert all(m.version(k)==v for k,v in [('numpy','2.3.5'),('scikit-learn','1.9.0'),('streamlit','1.66.0')])" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $labPython -m pip install -r requirements.txt --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw 'Free local dependency setup failed. No paid fallback was attempted.' }
}
Write-Host 'First-Half Goals Lab: http://127.0.0.1:8501'
Write-Host 'Offline research only. Close this session or press Ctrl+C to stop the app.'
& $labPython -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless false
