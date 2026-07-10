@echo off
echo ========================================================
echo   正在啟動 HR 系統 & 稽核後台 (管理員模式)
echo ========================================================

echo 1. 正在背景啟動 Companion 服務...
echo 2. 正在開啟 [風控稽核後台]...
start http://127.0.0.1:5001

cd /d D:\HR\hr-app
.venv\Scripts\python.exe app.py
