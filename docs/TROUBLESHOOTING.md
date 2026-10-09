# 🔍 FastTranslate - Troubleshooting & Known Issues Guide

Tổng hợp các sự cố thường gặp trong quá trình vận hành FastTranslate trên Windows, nguyên nhân cốt lõi và phương pháp khắc phục.

---

## 1. Sự cố: Phím tắt (`Alt + D` hoặc `Alt + Shift + D`) không phản hồi

### Triệu chứng
Bấm tổ hợp phím nhưng không thấy popup dịch xuất hiện hoặc màn hình chụp không kích hoạt.

### Nguyên nhân và cách xử lý

#### A. Trùng lặp tiến trình chạy ngầm (Orphan Processes)
- **Nguyên nhân**: Một phiên làm việc cũ của `python.exe` hoặc `pythonw.exe` đang chạy ngầm và giữ hook bàn phím cũ, khiến phiên mới không đăng ký được hotkey.
- **Cách xử lý**:
  Mở PowerShell hoặc Task Manager và tắt các tiến trình Python cũ:
  ```powershell
  Get-Process python*, pythonw* | Stop-Process -Force
  ```
  Sau đó khởi động lại ứng dụng bằng `run.bat` hoặc `run_debug.bat`.

#### B. Xung đột cấp quyền ứng dụng (Windows UIPI - User Interface Privilege Isolation)
- **Nguyên nhân**: Nếu bạn đang focus vào một ứng dụng chạy dưới quyền **Administrator** (ví dụ: Task Manager, Command Prompt Admin, Registry Editor), Windows sẽ chặn các sự kiện phím tắt từ ứng dụng cấp User thông thường.
- **Cách xử lý**: Chạy FastTranslate với quyền Administrator nếu bạn thường xuyên thao tác trên các cửa sổ hệ thống Admin.

#### C. Xung đột phím tắt với ứng dụng khác
- **Nguyên nhân**: Phím `Alt + D` là phím tắt mặc định để chuyển con trỏ vào thanh địa chỉ trên Google Chrome / Microsoft Edge / File Explorer.
- **Cách xử lý**: Đảm bảo module `hotkey_listener.py` bắt sự kiện phím toàn cục chuẩn xác hoặc đổi phím tắt trong `~/.fast_translate/config.json` (ví dụ: `ctrl+shift+x`, `alt+q`...).

---

## 2. Sự cố: Không thấy Tray Icon ở góc màn hình

### Triệu chứng
Ứng dụng đã chạy nhưng không thấy biểu tượng chữ **T** ở góc dưới bên phải màn hình.

### Nguyên nhân và cách xử lý
- **Khay hệ thống bị ẩn (Overflow Menu)**: Windows mặc định gom các biểu tượng mới vào menu mũi tên `^` ở Taskbar. Nhấp vào mũi tên `^` để kiểm tra và kéo biểu tượng chữ **T** ra ngoài Taskbar chính.
- **Định dạng Icon**: Windows Tray Icon yêu cầu file `.ico` chứa các kích thước chuẩn: `16x16`, `24x24`, `32x32`, `48x48`. File `assets/icon.ico` đã được tích hợp đầy đủ các độ phân giải này.

---

## 3. Sự cố: Tính năng khởi động cùng Windows không hoạt động sau khi restart

### Triệu chứng
Khởi động lại máy tính nhưng ứng dụng không tự bật, phải chạy lệnh thủ công.

### Nguyên nhân và cách xử lý
- **Sai thư mục làm việc (Working Directory)**: Khi Windows kích hoạt một script từ thư mục `shell:startup`, thư mục làm việc mặc định thường là `C:\Windows\System32` thay vì thư mục dự án `fast-translate`.
- **Cách xử lý**:
  Trong `src/core/autostart.py`, cấu hình shortcut trỏ trực tiếp đến `fast_translate.vbs` với WorkingDirectory được thiết lập tường minh là thư mục gốc của dự án.
  Kiểm tra thư mục startup bằng cách bấm `Win + R`, gõ `shell:startup` và kiểm tra shortcut `FastTranslate.lnk`.

---

## 4. Sự cố: Dịch OCR bị chậm hoặc thông báo "⏳ Vui lòng chờ..." quá lâu

### Triệu chứng
Sau khi quét vùng màn hình, popup hiện thông báo chờ lâu mới ra kết quả.

### Nguyên nhân và cách xử lý
- **Tác vụ đồng bộ trên Main Thread**: Đã được giải quyết bằng việc bọc quá trình OCR và Translation trong worker riêng biệt.
- **Đường truyền Internet**: Bản dịch sử dụng API Google Translate trực tuyến. Nếu mạng chập chờn, thời gian phản hồi có thể lâu hơn bình thường.
- **Vùng chọn quá nhỏ hoặc mờ**: Windows OCR hoạt động tối ưu với văn bản rõ nét và độ cao ký tự tối thiểu từ 15-20 pixels. Tránh quét vùng quá mờ hoặc chỉ chứa các đường viền đồ họa không có ký tự.
