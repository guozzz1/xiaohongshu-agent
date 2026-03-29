@echo off
set EDGE1=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
set EDGE2=C:\Program Files\Microsoft\Edge\Application\msedge.exe
if exist "%EDGE1%" (
    start "" "%EDGE1%" --remote-debugging-port=9222 --user-data-dir=D:\edge_xhs_cdp
) else if exist "%EDGE2%" (
    start "" "%EDGE2%" --remote-debugging-port=9222 --user-data-dir=D:\edge_xhs_cdp
) else (
    echo Edge not found
    pause
    exit /b 1
)
echo Edge started on port 9222
echo Please login to xiaohongshu, then run: python main.py
pause
