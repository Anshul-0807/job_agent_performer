@echo off
title AI Job Agent - FREE Groq Edition
color 0B

:MENU
cls
echo.
echo  =====================================================
echo   AI JOB AGENT  ^|  FREE  ^|  Groq Powered
echo   QA Engineer / Manual Tester Job Search
echo  =====================================================
echo.
echo   What do you want to do?
echo.
echo   [1] FULL RUN     - Scrape + Score + Apply (recommended)
echo   [2] DRY RUN      - Test everything, no real applications
echo   [3] SCRAPE ONLY  - Just find jobs, don't apply yet
echo   [4] APPLY ONLY   - Apply from last scored list
echo   [5] RE-SCORE     - Re-score jobs with Groq AI
echo   [6] HIGH QUALITY - Only apply to score 75 and above
echo   [7] EXIT
echo.
set /p choice="  Enter your choice (1-7): "

if "%choice%"=="1" goto FULL
if "%choice%"=="2" goto DRY
if "%choice%"=="3" goto SCRAPE
if "%choice%"=="4" goto APPLY
if "%choice%"=="5" goto MATCH
if "%choice%"=="6" goto HIGH
if "%choice%"=="7" goto END
goto MENU

:FULL
echo.
echo  Starting FULL RUN...
venv\Scripts\python main.py
goto DONE

:DRY
echo.
echo  Starting DRY RUN (no real applications)...
venv\Scripts\python main.py --dry-run
goto DONE

:SCRAPE
echo.
echo  Scraping jobs only...
venv\Scripts\python main.py --scrape-only
goto DONE

:APPLY
echo.
echo  Applying to scored jobs...
venv\Scripts\python main.py --apply-only
goto DONE

:MATCH
echo.
echo  Re-scoring jobs with Groq AI...
venv\Scripts\python main.py --match-only
goto DONE

:HIGH
echo.
echo  Applying to HIGH QUALITY matches only (score 75+)...
venv\Scripts\python main.py --min-score 75
goto DONE

:DONE
echo.
echo  =====================================================
echo   Done! Press any key to return to menu.
echo  =====================================================
pause >nul
goto MENU

:END
echo.
echo  Goodbye! Good luck with your job search!
echo.
