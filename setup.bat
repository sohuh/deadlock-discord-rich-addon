@echo off
title Deadlock Discord RPC - Setup
echo =============================================
echo Deadlock Discord Rich Presence Setup
echo =============================================
echo.
echo Installing required dependencies...
echo.

pip install -r requirements.txt

echo.
echo =============================================
echo Setup complete!
echo =============================================
echo.
echo Next steps:
echo 1. Edit deadlock_discord_rpc.py and add your Discord Client ID
echo 2. Run run.bat to start the application
echo.
pause
