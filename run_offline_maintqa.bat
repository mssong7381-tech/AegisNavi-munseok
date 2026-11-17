@echo off
chcp 65001 > nul
title AegisNavi-Pro - 선박정비 지능형 통합 관제 AI

echo =======================================================================
echo    ⚓ AegisNavi-Pro - 선박정비 지능형 통합 관제 오프라인 AI 기동
echo    (인터넷 및 외부 연결 없이 로컬 http://localhost:8080 에서 단독 구동)
echo =======================================================================
echo.

cd /d "%~dp0"

echo [1/3] 로컬 LLM 추론 엔진(Ollama) 상태 확인 중...
powershell -Command "if (-not (Get-Process -Name '*ollama*' -ErrorAction SilentlyContinue)) { Start-Process -FilePath '%LOCALAPPDATA%\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 2; Write-Host '  -> Ollama 데몬 백그라운드 기동 완료' } else { Write-Host '  -> Ollama 데몬 정상 실행 중' }"

echo [2/3] 브라우저 자동 오픈 예약 (http://localhost:8080)...
start "" cmd /c "timeout /t 3 /nobreak > nul && start http://localhost:8080"

echo [3/3] Python HTTP 서버 기동 중...
echo    접속 주소: http://localhost:8080 또는 http://127.0.0.1:8080
echo.
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" maintqa_web.py

pause
