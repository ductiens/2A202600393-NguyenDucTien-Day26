# SQLite Lab MCP Server (FastMCP + SQLite)

Project nay hoan thien lab MCP server voi:

- Tool `search`
- Tool `insert`
- Tool `aggregate`
- Resource `schema://database`
- Resource template `schema://table/{table_name}`

Server dung SQLite va co validate an toan cho table/column/operator/aggregate.

## 1) Cau truc du an

```text
implementation/
  __init__.py
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  tests/
    test_server.py
requirements.txt
```

## 2) Setup moi truong (Windows - PowerShell)

Neu ban muon dung dung Python path ban gui:

```powershell
& "D:\New folder\python.exe" -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Hoac khong activate, ban co the goi truc tiep:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Neu gap loi `No matching distribution found for fastmcp`, hay dung Python 3.11:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Khoi tao database

```powershell
python implementation\init_db.py
```

Ket qua mong doi: in ra duong dan `lab.db` vua duoc tao.

## 4) Chay server MCP (stdio mac dinh)

```powershell
python implementation\mcp_server.py
```

## 5) Verify nhanh (khong can client ngoai)

Script nay dung `fastmcp.Client` de kiem tra:
- discover tools/resources/templates
- goi tool hop le
- goi loi va nhan error ro rang

```powershell
python implementation\verify_server.py
```

## 6) Chay test

```powershell
pytest -q
```

## 7) Chay MCP Inspector (khuyen nghi)

```powershell
.\implementation\start_inspector.ps1 -PythonExe "D:\New folder\python.exe"
```

## 8) Vi du cau hinh client MCP

### Codex (`~/.codex/config.toml`)

```toml
[mcp_servers.sqlite_lab]
command = "python"
args = ["D:/Vin/Github_Lab/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"]
```

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python",
      "args": [
        "D:/Vin/Github_Lab/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"
      ]
    }
  }
}
```

## 9) Tool contract tom tat

### `search`

Input chinh:
- `table`: ten bang
- `columns`: danh sach cot (optional)
- `filters`: danh sach filter dang `{"column","op","value"}`
- `order_by`, `descending`, `limit`, `offset`

Output:
- metadata phan trang + `rows`

### `insert`

Input:
- `table`
- `values` (object key-value, khong duoc rong)

Output:
- payload vua insert (kem ID sinh tu dong neu co)

### `aggregate`

Input:
- `table`
- `metric`: `count|avg|sum|min|max`
- `column` (bat buoc cho moi metric tru `count`)
- `filters` (optional)
- `group_by` (optional)

Output:
- danh sach dong aggregate trong `rows`

## 10) Validation da trien khai

- reject bang khong ton tai
- reject cot khong ton tai
- reject operator khong ho tro
- reject metric khong ho tro
- reject insert rong
- dung query parameterized cho gia tri dau vao
