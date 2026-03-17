@echo off
echo Fixing Unicode escapes in Python files...
cd /d G:\projects\final_trading\Project2

echo.
echo Fixing websocket_wrapper.py...
powershell -Command "(Get-Content angel_api/websocket_wrapper.py) -replace '\\\\u2705', '' | Set-Content angel_api/websocket_wrapper.py"

echo.
echo Fixing symbol_loader.py...
powershell -Command "(Get-Content utils/symbol_loader.py) -replace '\\\\u2705', '' | Set-Content utils/symbol_loader.py"
powershell -Command "(Get-Content utils/symbol_loader.py) -replace '\\\\U0001f4cb', '' | Set-Content utils/symbol_loader.py"

echo.
echo Fixing simple_manager.py...
powershell -Command "(Get-Content excel/simple_manager.py) -replace '\\\\u2705', '' | Set-Content excel/simple_manager.py"

echo.
echo Fixing swv7.py...
powershell -Command "(Get-Content swv7.py) -replace '\\\\u2705', '' | Set-Content swv7.py"
powershell -Command "(Get-Content swv7.py) -replace '\\\\U0001f7e2', '' | Set-Content swv7.py"

echo.
echo Done! Now run your app.
pause