@echo off
title AI Job Agent - Setup
color 0A
echo.
echo  =====================================================
echo   AI JOB AGENT  ^|  FREE Groq Version  ^|  Setup
echo   For: Your Name ^| New Laptop Setup
echo  =====================================================
echo.

echo [STEP 1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate
echo   Done!

echo.
echo [STEP 2/5] Installing all Python packages from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip failed. Make sure Python is installed.
    pause
    exit /b 1
)
echo   Done!

echo.
echo [STEP 3/5] Installing Playwright browser (Chromium)...
playwright install chromium
echo   Done!

echo.
echo [STEP 4/5] Creating required folders and files...
if not exist "config"           mkdir config
if not exist "output"           mkdir output
if not exist "logs"             mkdir logs
if not exist "scripts"          mkdir scripts
if not exist "config\__init__.py"   type nul > config\__init__.py
if not exist "scripts\__init__.py"  type nul > scripts\__init__.py
echo   Done!

echo.
echo [STEP 5/5] Checking Groq API key...
if exist "config\settings.py" (
    findstr /C:"GROQ_API_KEY = \"\"" "config\settings.py" >nul 2>&1
    if %errorlevel% equ 0 (
        echo.
        echo  !! GROQ_API_KEY is still empty !!
        echo.
        echo  Please do this now:
        echo  1. Go to https://console.groq.com/keys
        echo  2. Create a free account (no credit card needed)
        echo  3. Copy your API key
        echo  4. Open config\settings.py and paste it into GROQ_API_KEY
        echo.
    ) else (
        echo   Groq API key found!
    )
) else (
    echo   config\settings.py not found - open it and add your Groq API key.
)

echo.
echo  =====================================================
echo   Setup Complete!
echo  =====================================================
echo.
echo  NEXT STEPS:
echo  1. Get a free API key at https://console.groq.com/keys
echo  2. Open config\settings.py and paste it into GROQ_API_KEY
echo  3. Fill in YOUR details:
echo     - Name: Your Full Name
echo     - Email: your.email@example.com
echo     - Phone: +91-XXXXXXXXXX
echo  4. Add your resume as config\resume.pdf
echo  5. Double-click RUN.bat to start!
echo.
pause