@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    py -m venv .venv
)

.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install pyinstaller

rem Run migrations against the local dev database so it stays current
.venv\Scripts\python.exe database\bootstrap.py

rem Build the exe. Schema SQL is bundled; the dev database itself is NOT
rem (the exe creates its own database folder next to itself on first run).
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name LifeLinkAI --add-data "templates;templates" --add-data "static;static" --add-data "database\trust_schema.sql;database" wsgi.py

echo.
echo Executable created at dist\LifeLinkAI.exe
echo Double-click it: it starts the server, creates its database next to
echo the exe, and opens the landing page in your browser.
pause
