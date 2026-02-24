conda activate StockDataParser
cd ..
[Environment]::SetEnvironmentVariable('DEBUG', 'False', 'User')
python .\tdx\AutoJingJia.py
pause