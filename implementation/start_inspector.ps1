param(
    [string]$PythonExe = "python"
)

$serverPath = (Join-Path $PSScriptRoot "mcp_server.py") -replace "\\","/"
$pythonPath = $PythonExe -replace "\\","/"
npx -y @modelcontextprotocol/inspector $pythonPath $serverPath
