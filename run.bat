@echo off
title APEX AI
echo.
echo  ╔══════════════════════════════╗
echo  ║   APEX AI — Starting Up...   ║
echo  ╚══════════════════════════════╝
echo.
echo  Installing dependencies...
pip install -r requirements.txt -q
echo.
echo  Server starting at http://localhost:8000
echo  Press Ctrl+C to stop.
echo.
start "" http://localhost:8000
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
