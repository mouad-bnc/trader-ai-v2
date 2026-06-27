@echo off
title Build Trader AI v2
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --name "Trader AI v2" launcher.py
copy app.py dist\app.py
copy trader_core.py dist\trader_core.py
copy config.json dist\config.json
echo.
echo Build termine.
echo Ton application est ici: dist\Trader AI v2.exe
echo Double-clique dessus pour lancer Trader AI.
pause
