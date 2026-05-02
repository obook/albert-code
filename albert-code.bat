@echo off
REM Lanceur albert-code -- Windows
REM Sans argument : affiche un menu (lancer / installer / desinstaller / quitter).
REM Avec arguments : execute albert-code en mode direct.
REM Usage : albert-code.bat [options] [PROMPT]

REM %~dp0 = dossier du script (d=drive, p=path, 0=argument 0)
set SCRIPT_DIR=%~dp0
REM Supprimer le \ final pour eviter les doubles \ dans les chemins
if "%SCRIPT_DIR:~-1%"=="\" set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set VENV_DIR=%SCRIPT_DIR%\.venv

REM Si des arguments sont fournis, mode direct (pas de menu, pas de check console)
if not "%~1"=="" goto :prepare

REM Aucun argument : verifier d'abord la console avant d'afficher le menu.
REM Le menu et la TUI ne fonctionnent que dans Windows Terminal.
if not "%WT_SESSION%"=="" goto :menu
echo.
echo La console actuelle ne supporte pas l'interface d'Albert Code.
echo L'invite de commande classique ^(cmd.exe^) ne sait pas afficher la TUI Textual.
echo.
echo Solutions :
echo   1. Installer Windows Terminal ^(https://aka.ms/terminal^) et y relancer ce .bat.
echo   2. Utiliser le mode programmatique sans TUI : albert-code.bat -p "votre prompt"
echo.
pause
exit /b 1

:menu
cls
echo.
echo ===========================================
echo                 ALBERT CODE
echo ===========================================
echo.
echo  1. Lancer Albert Code
echo  2. Installer la commande "albert-code" dans le PATH utilisateur
echo  3. Desinstaller la commande "albert-code" du PATH utilisateur
echo  4. Quitter
echo.
set /p CHOICE=Choix [1-4] :
echo.
if "%CHOICE%"=="1" goto :prepare
if "%CHOICE%"=="2" goto :do_install_path
if "%CHOICE%"=="3" goto :do_uninstall_path
if "%CHOICE%"=="4" exit /b 0
echo Choix invalide.
timeout /t 2 >nul
goto :menu

:do_install_path
echo Ajout de "%SCRIPT_DIR%" au PATH utilisateur...
powershell -NoProfile -Command "$dir = '%SCRIPT_DIR%'; $current = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($current -notlike ('*' + $dir + '*')) { if ([string]::IsNullOrEmpty($current)) { $new = $dir } else { $new = $current.TrimEnd(';') + ';' + $dir }; [Environment]::SetEnvironmentVariable('Path', $new, 'User'); Write-Host 'Ajoute.' } else { Write-Host 'Deja present, aucun changement.' }"
echo.
echo Ouvrir une nouvelle fenetre Windows Terminal pour utiliser la commande "albert-code" depuis n'importe quel dossier.
echo.
pause
goto :menu

:do_uninstall_path
echo Retrait de "%SCRIPT_DIR%" du PATH utilisateur...
powershell -NoProfile -Command "$dir = '%SCRIPT_DIR%'; $current = [Environment]::GetEnvironmentVariable('Path', 'User'); if ([string]::IsNullOrEmpty($current)) { Write-Host 'PATH utilisateur vide, rien a faire.' } else { $entries = $current -split ';' | Where-Object { $_ -ne $dir -and $_ -ne '' }; $new = $entries -join ';'; [Environment]::SetEnvironmentVariable('Path', $new, 'User'); Write-Host 'Retire.' }"
echo.
pause
goto :menu

:prepare
REM Verifier que python est disponible
where python >nul 2>&1
if errorlevel 1 (
    echo Erreur : python introuvable. Installer Python 3.12+ avant de continuer.
    pause
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
REM (verification par chemin absolu : `where albert-code` retournerait aussi
REM ce script .bat puisqu'il porte le meme nom dans le dossier courant)
if not exist "%VENV_DIR%\Scripts\albert-code.exe" goto :install

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
REM Appel par chemin absolu pour eviter la recursion : `where albert-code`
REM trouve d'abord ce script .bat dans le dossier courant, puis l'.exe du venv
"%VENV_DIR%\Scripts\albert-code.exe" %*
REM Pause finale uniquement si la fenetre s'est ouverte par double-clic et qu'on
REM est entre par le menu (sinon, retour normal au shell appelant).
if "%~1"=="" pause
