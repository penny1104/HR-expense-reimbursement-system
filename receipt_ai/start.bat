@echo off
REM ============================================================
REM  啟動收據辨識 API(單一視窗)
REM  OCR 子程序會自動啟動,不需另外開服務、不走 HTTP。
REM ============================================================
cd /d "%~dp0"
set "PYTHON_EXE=D:\conda_envs\receipt_app\python.exe"
if not exist "%PYTHON_EXE%" (
    if exist "%USERPROFILE%\miniconda3\envs\receipt_app\python.exe" (
        set "PYTHON_EXE=%USERPROFILE%\miniconda3\envs\receipt_app\python.exe"
    ) else if exist "%USERPROFILE%\anaconda3\envs\receipt_app\python.exe" (
        set "PYTHON_EXE=%USERPROFILE%\anaconda3\envs\receipt_app\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
)
"%PYTHON_EXE%" app.py
pause
