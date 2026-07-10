@echo off
REM 批次測試 imgs/ 內的範例圖(OCR 子程序自動啟動)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
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
"%PYTHON_EXE%" -X utf8 test.py %*
pause
