# 🛠️ FastTranslate - Development Guide & Git Flow Standard

Hướng dẫn phát triển, quy chuẩn mã nguồn, quy trình Git Flow và kiểm thử tự động cho dự án FastTranslate.

---

## 1. Thiết lập môi trường phát triển (Local Setup)

### Yêu cầu tiên quyết
- **Hệ điều hành**: Windows 10 (1903 trở lên) hoặc Windows 11 (yêu cầu để sử dụng Windows Media OCR).
- **Python**: Phiên bản 3.10 trở lên (khuyến nghị 3.11 - 3.14).
- **Git**: Đã cài đặt Git for Windows.

### Các bước cài đặt
```powershell
# 1. Di chuyển vào thư mục dự án
cd d:\workspace\tools\fast-translate

# 2. Tạo virtual environment (nếu chưa có)
python -m venv .venv

# 3. Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1

# 4. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 2. Quy chuẩn Git Flow

Dự án áp dụng mô hình phân nhánh chuẩn **Git Flow**:

```text
main (production-ready, stable releases)
  │
  └── develop (nhánh tích hợp chính)
        ├── feature/ten-tinh-nang
        ├── bugfix/ten-loi
        └── hotfix/sua-loi-gap
```

### 2.1. Quy ước đặt tên nhánh (Branch Naming)
| Tiền tố | Mục đích | Ví dụ |
| :--- | :--- | :--- |
| `feature/` | Phát triển tính năng mới | `feature/multi-language-support`, `feature/history-panel` |
| `bugfix/` | Sửa lỗi trong quá trình phát triển | `bugfix/clipboard-encoding-issue` |
| `hotfix/` | Sửa lỗi khẩn cấp trên nhánh production | `hotfix/hotkey-conflict-on-startup` |
| `refactor/`| Tái cấu trúc mã nguồn không đổi tính năng | `refactor/ocr-worker-threading` |
| `docs/` | Cập nhật tài liệu kỹ thuật | `docs/update-architecture-diagram` |

### 2.2. Quy ước thông điệp Commit (Conventional Commits)
Định dạng: `<type>(<scope>): <mô tả ngắn>`

Các loại `<type>`:
- **`feat`**: Tính năng mới (new feature).
- **`fix`**: Sửa lỗi (bug fix).
- **`docs`**: Thay đổi hoặc bổ sung tài liệu.
- **`style`**: Định dạng code, dấu cách, format không ảnh hưởng logic.
- **`refactor`**: Tái cấu trúc code (không sửa bug cũng không thêm feat).
- **`perf`**: Cải thiện hiệu năng (performance improvement).
- **`test`**: Bổ sung hoặc sửa đổi unit/integration test.
- **`chore`**: Cập nhật build script, cấu hình tooling, dependencies.

**Ví dụ:**
```bash
git commit -m "feat(ui): add pin button and copy translation shortcut"
git commit -m "fix(hotkey): resolve keyboard hook collision with other desktop apps"
git commit -m "docs: add architecture and troubleshooting guides"
```

---

## 3. Chạy ứng dụng trong quá trình phát triển

### Chế độ Debug (Có cửa sổ log trực quan)
Chạy bằng file batch:
```powershell
.\run_debug.bat
```
Hoặc qua Python trực tiếp:
```powershell
.\.venv\Scripts\python -m src.main --debug
```

### Chế độ chạy ngầm (Silent mode)
```powershell
wscript fast_translate.vbs
```

---

## 4. Kiểm thử tự động (Testing)

Trước khi commit hoặc merge code, luôn chạy bộ kiểm thử để đảm bảo không phát sinh regression:

```powershell
# Chạy toàn bộ test suite
.\.venv\Scripts\python -m unittest discover tests -v

# Chạy riêng bài test bằng chứng (Evidence tests)
.\.venv\Scripts\python -m unittest tests/test_evidence.py -v

# Chạy test module OCR
.\.venv\Scripts\python -m unittest tests/test_ocr.py -v

# Chạy test module dịch thuật
.\.venv\Scripts\python -m unittest tests/test_translator.py -v
```

---

## 5. Quy trình hoàn thiện một Feature / Bugfix

1. Checkout từ `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/<feature-name>
   ```
2. Thực hiện thay đổi code, cập nhật tài liệu liên quan nếu thay đổi kiến trúc/flow.
3. Viết và chạy unit tests để xác minh tính năng.
4. Commit theo chuẩn Conventional Commits.
5. Merge về `develop` hoặc tạo Pull/Merge Request.
