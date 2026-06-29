@echo off
chcp 65001 >nul
echo ============================================================
echo   Agent 多智能体代码生成系统 — 环境安装
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)
echo [OK] Python 已就绪

REM 创建虚拟环境（可选）
if not exist venv (
    echo [安装] 创建虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate.bat

REM 安装依赖
echo [安装] Python 依赖...
pip install -r requirements.txt -q

REM 检查 Node.js（目标运行时，框架本身不需要）
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 未找到 Node.js（生成的项目需要，框架本身不需要）
)

REM 复制环境变量模板
if not exist .env (
    copy .env.example .env >nul
    echo [OK] .env 已从模板创建，请编辑填入 API Key
)

echo.
echo ============================================================
echo   安装完成！
echo   1. 编辑 .env 填入 OPENAI_API_KEY
echo   2. python brainAgent/basic.py "你的需求描述"
echo ============================================================
pause
