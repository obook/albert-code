@echo off
REM Lanceur albert-code -- Windows
REM
REM Sans argument : lance la TUI (relancee dans Windows Terminal si besoin).
REM Avec arguments : execute albert-code en mode direct.
REM
REM Sous-commandes :
REM   albert-code.bat --install     -> ouvre un menu de gestion du PATH
REM                                    (installer / desinstaller / lancer / quitter)
REM   albert-code.bat --uninstall   -> retire le dossier du PATH utilisateur
REM
REM Usage : albert-code.bat [options] [PROMPT]

REM %~dp0 = dossier du script (d=drive, p=path, 0=argument 0)
set SCRIPT_DIR=%~dp0
REM Supprimer le \ final pour eviter les doubles \ dans les chemins
if "%SCRIPT_DIR:~-1%"=="\" set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set VENV_DIR=%SCRIPT_DIR%\.venv

REM Dispatch des arguments :
REM   --install   -> ouvre le menu de gestion du PATH
REM   --uninstall -> retire le dossier du PATH (sortie immediate)
REM   <prompt>    -> mode direct (pas de menu, pas de check console)
REM   (vide)      -> lance la TUI (necessite Windows Terminal)
if /i "%~1"=="--install" goto :menu
if /i "%~1"=="--uninstall" goto :cli_uninstall_path
if not "%~1"=="" goto :prepare

:tui_launch
REM Aucun argument : la TUI ne fonctionne que dans Windows Terminal.
if not "%WT_SESSION%"=="" goto :prepare

REM Garde anti-boucle : si on a deja tente un relancement, montrer l'aide
REM directement plutot que de relancer indefiniment (au cas ou WT_SESSION
REM ne serait pas propagee correctement par Windows Terminal).
if defined _ALBERT_RELAUNCHED goto :show_console_error

REM Tenter le relancement automatique dans Windows Terminal s'il est installe.
where wt >nul 2>&1
if errorlevel 1 goto :show_console_error

echo Console actuelle non supportee, relancement dans Windows Terminal...
set _ALBERT_RELAUNCHED=1
start "" wt.exe new-tab --title "Albert Code" -d "%CD%" cmd.exe /k "%~f0"
exit /b 0

:show_console_error
echo.
echo ===========================================================
echo  Console non supportee
echo ===========================================================
echo.
echo L'invite de commande classique ^(cmd.exe^) ne sait pas afficher
echo l'interface d'Albert Code. Il faut utiliser Windows Terminal.
echo.
echo --- Si Windows Terminal n'est pas installe ---
echo.
echo   1. Ouvrir le Microsoft Store depuis le menu Demarrer.
echo   2. Rechercher "Windows Terminal" ou ouvrir https://aka.ms/terminal
echo   3. Cliquer sur "Obtenir" ou "Installer".
echo.
echo --- Une fois Windows Terminal installe ---
echo.
echo   1. Fermer cette fenetre.
echo   2. Ouvrir Windows Terminal depuis le menu Demarrer
echo      ^(rechercher "Terminal" ; icone noire avec un chevron^).
echo   3. Dans Windows Terminal, taper :
echo.
echo         cd "%SCRIPT_DIR%"
echo         .\albert-code.bat
echo.
echo --- Alternative sans interface graphique ---
echo.
echo   Le mode programmatique fonctionne dans cette console :
echo.
echo         albert-code.bat -p "votre prompt"
echo.
echo ===========================================================
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
if "%CHOICE%"=="1" goto :tui_launch
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

REM Variante CLI pour --uninstall : meme action que l'option du menu, mais
REM sortie immediate (pas de retour vers le menu, pas de pause finale).
:cli_uninstall_path
echo Retrait de "%SCRIPT_DIR%" du PATH utilisateur...
powershell -NoProfile -Command "$dir = '%SCRIPT_DIR%'; $current = [Environment]::GetEnvironmentVariable('Path', 'User'); if ([string]::IsNullOrEmpty($current)) { Write-Host 'PATH utilisateur vide, rien a faire.' } else { $entries = $current -split ';' | Where-Object { $_ -ne $dir -and $_ -ne '' }; $new = $entries -join ';'; [Environment]::SetEnvironmentVariable('Path', $new, 'User'); Write-Host 'Retire.' }"
exit /b 0

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
for /f "tokens=*" %%H in ('certutil -hashfile "%PYPROJECT%" SHA256 ^| findstr /v ":"') do (
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
