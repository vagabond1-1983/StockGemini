conda activate StockDataParser1
cd "C:\Resources\StockGemini"
[Environment]::SetEnvironmentVariable('DEBUG', 'False', 'User')
python .\tdx\AutoJingJia.py
pause