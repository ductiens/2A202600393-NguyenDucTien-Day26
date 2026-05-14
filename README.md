# Lab MCP SQLite (FastMCP)

## 1. Giới thiệu

Dự án này triển khai MCP Server bằng FastMCP kết nối SQLite, đáp ứng đầy đủ yêu cầu lab:

- Tool `search`
- Tool `insert`
- Tool `aggregate`
- Resource `schema://database`
- Resource template `schema://table/{table_name}`
- Kiểm thử tự động bằng `pytest`
- Verify nhanh bằng script `verify_server.py`
- Kiểm tra thủ công bằng MCP Inspector

## 2. Cấu trúc dự án

```text
implementation/
  __init__.py
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  start_inspector.ps1
  tests/
    test_server.py
demo-assets/
  screenshots/
  video/
requirements.txt
```

## 3. Yêu cầu môi trường

- Windows + PowerShell
- Python khuyến nghị: `3.11.x`
- Có thể dùng Python khác nếu cài được `fastmcp`

Lưu ý: nếu Python 3.14 báo lỗi `No matching distribution found for fastmcp`, hãy chuyển sang Python 3.11.

## 4. Cài đặt

### Cách 1: dùng Python bạn chỉ định

```powershell
& "D:\New folder\python.exe" -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Cách 2: dùng Python 3.11 (khuyến nghị ổn định)

```powershell
py -3.11 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Khởi tạo database

```powershell
python implementation\init_db.py
```

Kết quả mong đợi: in ra đường dẫn file `implementation/lab.db`.

## 6. Chạy test tự động

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Kết quả mong đợi:
- `3 passed`

## 7. Verify nhanh toàn bộ server

```powershell
python implementation\verify_server.py
```

Script này sẽ kiểm tra:
- discover 3 tools
- discover resource + resource template
- gọi thành công `search`, `insert`, `aggregate`
- đọc `schema://database`, `schema://table/students`
- kiểm tra lỗi có chủ đích (`missing_table`)

## 8. Chạy MCP server

```powershell
python implementation\mcp_server.py
```

Server chạy theo `stdio`, nên không có giao diện riêng.  
Để test bằng UI, dùng MCP Inspector ở mục bên dưới.

## 9. Chạy MCP Inspector

```powershell
.\implementation\start_inspector.ps1 -PythonExe ".\venv\Scripts\python.exe"
```

Sau đó mở link Inspector được in ra terminal và bấm `Connect`.

## 10. Payload mẫu để test 3 tools

### `search`

```json
{
  "table": "students",
  "filters": [
    {"column": "cohort", "op": "=", "value": "A1"}
  ],
  "columns": ["id", "name", "cohort", "age"],
  "limit": 20,
  "offset": 0,
  "order_by": "id",
  "descending": false
}
```

### `insert`

```json
{
  "table": "students",
  "values": {
    "name": "Demo User",
    "cohort": "A1",
    "age": 22
  }
}
```

### `aggregate`

```json
{
  "table": "enrollments",
  "metric": "avg",
  "column": "score",
  "filters": null,
  "group_by": ["course_id"]
}
```

## 11. Test resources

- `schema://database`
- `schema://table/students`

## 12. Test lỗi (validation)

Payload lỗi mẫu:

```json
{"table":"missing_table"}
```

Kỳ vọng: báo lỗi rõ ràng `Unknown table 'missing_table'`.

## 13. Các rule an toàn đã triển khai

- Từ chối bảng không tồn tại
- Từ chối cột không tồn tại
- Từ chối operator không hỗ trợ
- Từ chối metric không hỗ trợ
- Từ chối insert rỗng
- Dùng truy vấn tham số hóa để tránh SQL injection qua giá trị đầu vào

## 14. Ví dụ cấu hình MCP client

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

## 15. Minh chứng demo

Thư mục gợi ý:

- Ảnh: `demo-assets/screenshots`
- Video: `demo-assets/video`

Bộ ảnh đã chuẩn hóa tên:

- `01_tool_search_success.png`
- `02_tool_insert_success.png`
- `03_tool_aggregate_success.png`
- `04_resource_schema_database.png`
- `05_resource_schema_students.png`
- `06_tool_search_error_unknown_table.png`

## 16. Lệnh nhanh tổng hợp

```powershell
.\venv\Scripts\activate
python implementation\init_db.py
.\venv\Scripts\python.exe -m pytest -q
python implementation\verify_server.py
python implementation\mcp_server.py
```

