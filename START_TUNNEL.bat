@echo off
chcp 65001 >nul
echo ====== Xiaoyu Loves Keke / HTTPS Tunnel ======
echo.
echo Keep START_WINDOWS model and web windows running.
echo Quick Tunnel address can CHANGE after restart.
echo Public address is displayed on a cloudflared output line.
echo.
where cloudflared >nul 2>nul
if errorlevel 1 (
 echo cloudflared was not found in PATH.
 echo Download: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
 pause
 exit /b 1
)
cloudflared tunnel --url http://127.0.0.1:7865
pause
