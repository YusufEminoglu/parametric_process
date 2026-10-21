@echo off
REM ============================================================================
REM  Parametric Process Practical Guide — capture harness
REM
REM  1) Runs every Processing algorithm in a real QGIS runtime against the real
REM     Tire İlçesi planning master and writes 4-panel composites.
REM  2) Starts the plugin's own local server on the same real data and drives it
REM     with Playwright to capture the real web studio.
REM  3) Rebuilds the guide HTML and the web-sized images.
REM
REM  Usage:
REM    run_practical_guide.bat
REM    run_practical_guide.bat --module parametric_optimization
REM ============================================================================
setlocal
cd /d "%~dp0"

set "QGIS_PY=C:\OSGeo4W\bin\python-qgis-ltr.bat"
if not exist "%QGIS_PY%" set "QGIS_PY=C:\OSGeo4W\bin\python-qgis.bat"
if not exist "%QGIS_PY%" (
    echo [ERROR] No QGIS Python found at C:\OSGeo4W\bin\python-qgis-ltr.bat
    exit /b 1
)

echo.
echo [1/3] Processing algorithms
"%QGIS_PY%" practical_guide_runner.py --all
if errorlevel 1 (
    echo [ERROR] Algorithm capture failed.
    exit /b 1
)

echo.
echo [2/3] Browser studio (real local server + Playwright)
start "" /b cmd /c "%QGIS_PY%" serve_real_data.py --port 18112 > serve.log 2>&1
REM give the server time to boot and stream the cadastral master
timeout /t 45 /nobreak >nul

node capture_ui.mjs --url http://127.0.0.1:18112/index.html --out screenshots/ui
if errorlevel 1 echo [WARN] Browser capture reported a problem - the algorithm panels are still complete.

echo.
echo [3/3] Guide + web images
where python >nul 2>nul && python build_guide.py || py -3 build_guide.py
where python >nul 2>nul && python optimize_images.py || py -3 optimize_images.py
where python >nul 2>nul && python build_guide.py || py -3 build_guide.py

echo.
echo Done. Open practical_guide.html
endlocal
