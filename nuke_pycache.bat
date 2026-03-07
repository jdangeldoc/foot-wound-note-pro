@echo off
cd /d "%~dp0"
echo Deleting __pycache__ folders recursively...
for /r %%D in (__pycache__) do if exist "%%D" rmdir /s /q "%%D"
echo Done.
pause
