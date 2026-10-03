@echo off
setlocal
cd /d %~dp0

if not exist .venv (
    echo Creating Python 3.12 virtual environment...
    py -3.12 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

where uvicorn >nul 2>nul
if errorlevel 1 (
    echo Installing PaddlePaddle CPU ^(Python 3.12^)...
    python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
    echo Installing remaining dependencies...
    python -m pip install -r requirements.txt
)

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000