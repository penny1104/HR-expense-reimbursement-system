@echo off
echo ========================================================
echo   正在啟動 HR 差旅報銷系統 (已整合 AI 辨識與風控)
echo ========================================================

echo 1. 正在背景啟動 Companion 服務...
echo 2. 正在自動開啟 [HR 差旅報銷系統]...
start http://127.0.0.1:3000

cd /d D:\HR\hr-app
.venv\Scripts\python.exe app.py
