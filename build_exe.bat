@echo off
setlocal

cd /d "%~dp0"

set APP_NAME=DCDC_clock_simulator
set APP_VERSION=v1.0.0
set ZIP_NAME=%APP_NAME%_%APP_VERSION%

echo ========================================
echo Build %APP_NAME% %APP_VERSION%
echo ========================================

REM 古いビルド結果を削除
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM PyInstallerでonedir形式ビルド
uv run pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "%APP_NAME%" ^
  --icon "icon\dc_icon.ico" ^
  --add-data "timing_config.xlsx;." ^
  main.py

echo.
echo ========================================
echo Build finished.
echo Output:
echo dist\%APP_NAME%\%APP_NAME%.exe
echo.
echo Recommended zip name:
echo %ZIP_NAME%.zip
echo ========================================
echo.

pause
