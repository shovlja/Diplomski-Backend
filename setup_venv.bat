@echo off
echo ======================================
echo  Setting up Python virtual environment
echo ======================================

:: Check if venv already exists
if exist venv (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install dependencies
if exist requirements.txt (
    echo Installing packages from requirements.txt...
    pip install -r requirements.txt
) else (
    echo WARNING: requirements.txt not found. Skipping package installation.
)

echo ======================================
echo  Setup complete. Virtual env is active.
echo ======================================
cmd /k
