@echo off
REM Quick database reset script for RecruiterRadar testing (Windows)

echo 🔄 RecruiterRadar Database Reset
echo =================================

REM Check if we're in the backend directory
if not exist "cleanup_database.py" (
    echo ❌ Error: Run this script from the backend\ directory
    pause
    exit /b 1
)

REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️  Warning: Virtual environment not found at .venv\Scripts\activate.bat
    echo Please activate it manually before running this script
    pause
    exit /b 1
)

echo 🎯 Performing full database reset (recommended for testing)...
echo    - Clearing all ChromaDB data
echo    - Reloading demo candidates
echo.

python cleanup_database.py --full-reset

if %errorlevel% equ 0 (
    echo.
    echo ✅ Database reset complete! Ready for testing uploads.
) else (
    echo.
    echo ❌ Database reset failed. Check the error messages above.
    pause
    exit /b 1
)

pause 