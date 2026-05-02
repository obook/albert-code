@echo off
REM Lanceur albert-code -- Windows
REM Cree le venv Python au premier lancement, puis lance albert-code.
REM Usage : albert-code.bat [options] [PROMPT]

REM %~dp0 = dossier du script (d=drive, p=path, 0=argument 0)
set SCRIPT_DIR=%~dp0
REM Supprimer le \ final pour eviter les doubles \ dans les chemins
if "%SCRIPT_DIR:~-1%"=="\" set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set VENV_DIR=%SCRIPT_DIR%\.venv

REM Verifier que python est disponible
where python >nul 2>&1
if errorlevel 1 (
    echo Erreur : python introuvable. Installe Python 3.12+ avant de continuer.
    exit /b 1
)

set INSTALL_MARKER=%VENV_DIR%\.albert-code-install-hash
set PYPROJECT=%SCRIPT_DIR%\pyproject.toml

REM Venv deja present : activer puis verifier la coherence
if exist "%VENV_DIR%" goto :activate

REM Premier lancement : creer le venv
echo Creation de l'environnement virtuel...
python -m venv "%VENV_DIR%"
if errorlevel 1 exit /b 1
call "%VENV_DIR%\Scripts\activate.bat"
goto :install

:activate
call "%VENV_DIR%\Scripts\activate.bat"

REM Calculer le hash de pyproject.toml pour detecter les changements
set CURRENT_HASH=
for /f "skip=1 tokens=*" %%H in ('certutil -hashfile "%PYPROJECT%" SHA256 ^| findstr /v ":"') do (
    if not defined CURRENT_HASH set CURRENT_HASH=%%H
)
set CURRENT_HASH=%CURRENT_HASH: =%

REM Si pas d'entry point ou hash different : reinstaller
where albert-code >nul 2>&1
if errorlevel 1 goto :install

if not exist "%INSTALL_MARKER%" goto :install
set /p STORED_HASH=<"%INSTALL_MARKER%"
if /i not "%STORED_HASH%"=="%CURRENT_HASH%" goto :install
goto :run

:install
echo Installation des dependances et du projet (mode editable)...
python -m pip install --upgrade --disable-pip-version-check pip >nul
pip install --disable-pip-version-check -e "%SCRIPT_DIR%"
if errorlevel 1 exit /b 1
if defined CURRENT_HASH (
    >"%INSTALL_MARKER%" echo %CURRENT_HASH%
)
echo Lancement de albert-code, veuillez patienter...
echo.

:run
albert-code %*
