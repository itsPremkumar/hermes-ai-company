@echo off
REM ================================================================
REM 🚀 MEMORY CLEANER — Run before opening VS Code / Chrome / heavy apps
REM Frees ~300+ MB of wasted RAM instantly
REM Safe — kills only non-essential user apps
REM ================================================================
echo.
echo === MEMORY CLEANER ===
echo Killing non-essential processes to free RAM...
echo.

REM --- WPS Office suite (~250 MB total) ---
taskkill /f /im wps.exe >nul 2>&1 && echo [OK] Killed WPS Office || echo [--] WPS not running
taskkill /f /im wpscenter.exe >nul 2>&1 && echo [OK] Killed WPS Center || echo [--] WPS Center not running
taskkill /f /im wpscloudsvr.exe >nul 2>&1 && echo [OK] Killed WPS Cloud Sync || echo [--] WPS Cloud not running
taskkill /f /im promecefpluginhost.exe >nul 2>&1 && echo [OK] Killed WPS CEF Plugin || echo [--] WPS CEF not running

REM --- Remote Desktop ---
taskkill /f /im AnyDesk.exe >nul 2>&1 && echo [OK] Killed AnyDesk || echo [--] AnyDesk not running

REM --- Optional: uncomment these if you don't use Phone Link ---
REM taskkill /f /im PhoneExperienceHost.exe >nul 2>&1 && echo [OK] Killed Phone Link

echo.
echo === Done! ===
echo.
REM Show free memory
for /f "tokens=2 delims==" %%a in ('wmic OS get FreePhysicalMemory /Value ^| find "="') do set FREE_KB=%%a
set /a FREE_MB=%FREE_KB%/1024
echo Free RAM: %FREE_MB% MB
echo.
echo Now you can open VS Code / Chrome without memory errors!
echo.
pause
