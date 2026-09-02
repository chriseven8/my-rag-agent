@echo off
setlocal
cd /d "%~dp0"
title my-rag-agent Web launcher

echo ==========================================
echo   my-rag-agent Web one-click launcher
echo ==========================================
echo.

echo [1/3] start database container (docker compose up -d)...
docker compose up -d
if errorlevel 1 echo   NOTE: start Docker Desktop first if the above reports an error.

set "PY=%~dp0backend\.venv\Scripts\python.exe"
if exist "%PY%" goto check_dist

echo.
echo [ERROR] backend venv python not found:
echo   %PY%
echo Run this setup once in git-bash:
echo   cd /e/AI-Workspace/my-rag-agent
echo   cd backend
echo   python -m venv .venv
echo   ./.venv/Scripts/python -m pip install -r requirements.txt
pause
exit /b 1

:check_dist
echo.
echo [2/3] check frontend build output...
if exist "frontend\dist\index.html" goto start_server
echo   no dist found - building frontend (requires Node.js on PATH)...
if exist "frontend\node_modules" goto do_build
echo   installing frontend dependencies (npm install)...
pushd frontend
call npm install
if errorlevel 1 goto npm_fail
popd

:do_build
pushd frontend
call npm run build
if errorlevel 1 goto build_fail
popd
goto start_server

:npm_fail
popd
echo   npm install failed - install Node.js and retry.
pause
exit /b 1

:build_fail
popd
echo   frontend build failed.
pause
exit /b 1

:start_server
echo.
echo [3/3] starting server at http://127.0.0.1:9081 ...
if /i not "%1"=="nobrowser" (
    start "browser" /b powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "$u='http://127.0.0.1:9081'; for($i=0;$i -lt 60;$i++){ Start-Sleep -Milliseconds 500; try{ $r=Invoke-WebRequest -UseBasicParsing -Uri ($u+'/api/health') -TimeoutSec 2; if($r.StatusCode -eq 200){ Start-Process $u; break } }catch{} }"
)
echo   A browser tab will open once the server is ready.
echo   Close this window or press Ctrl+C to stop the server.
echo.
pushd backend
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 9081
if errorlevel 1 (
    echo.
    echo Server exited abnormally - port 9081 already in use? Close other instances.
    pause
)
popd
endlocal
