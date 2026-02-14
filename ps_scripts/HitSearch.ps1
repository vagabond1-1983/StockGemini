conda activate StockDataParser
cd "D:\Resources\python\StockDataParser"
# 循环运行
$continue = $true
while ($continue) {
    try {
        python .\tdx\HitSearch.py
        # 根据脚本退出码判断是否继续
#         if ($LASTEXITCODE -eq 0) {
#             $continue = $false
#         }
    } catch {
        Write-Host "Error occurred, retrying..."
    }
#     Start-Sleep -Seconds 5
}