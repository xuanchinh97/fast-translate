# 📋 Changelog - FastTranslate

Mọi thay đổi đáng chú ý của dự án FastTranslate sẽ được ghi nhận tại file này.
Định dạng tuân theo [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) và phiên bản tuân theo [Semantic Versioning](https://semver.org/).

---

## [1.2.0] - 2026-10-13

### Added
- **Cho phép chỉnh sửa ô văn bản gốc (Editable Input)**: Người dùng có thể click sửa từ, câu hoặc nhập văn bản mới trực tiếp trong popup.
- **Tự động dịch thông minh (Debounce 600ms)**: Tự động gửi yêu cầu dịch sau khi người dùng ngừng gõ, không cần bấm thêm thao tác.
- **Phím tắt `Ctrl + Enter`**: Dịch ngay lập tức khi đang con trỏ ở ô nhập liệu.
- **Thanh công cụ nhanh**:
  - Nút **`🔄 Dịch lại`**: Kích hoạt dịch ngay bản dịch mới.
  - Nút **`✕ Xóa`**: Xóa nhanh nội dung ô nhập để nhập từ khác.
- **Bộ đếm ký tự & trạng thái thời gian thực**: Hiển thị số lượng ký tự và tiến trình dịch trực quan ở góc dưới popup.
- **Bảo vệ kết quả cũ (Race condition protection)**: Không ghi đè bản dịch cũ nếu người dùng đã thay đổi nội dung ô nhập.
- Bộ kiểm thử tự động `tests/test_popup_editable.py` cho tính năng chỉnh sửa ô input.

---

## [1.1.0] - 2026-10-09

### Added
- Khởi tạo quản lý mã nguồn chuẩn Git Flow và Conventional Commits.
- Bổ sung hệ thống tài liệu theo dõi luồng phát triển:
  - `docs/ARCHITECTURE.md`: Thiết kế kiến trúc và sơ đồ luồng dữ liệu (Data Flows).
  - `docs/DEVELOPMENT_GUIDE.md`: Quy chuẩn Git Flow, branch naming, commit message và hướng dẫn test.
  - `docs/TROUBLESHOOTING.md`: Cẩm nang xử lý sự cố phím tắt, icon tray, autostart và OCR.
- Bộ kiểm thử tự động xác minh tính năng `tests/test_evidence.py`.
- Tùy chọn icon độ phân giải cao đa kích thước (`assets/icon.ico`).

### Changed
- Cập nhật cơ chế đăng ký phím tắt toàn cục giảm thiểu xung đột.
- Chuẩn hóa cấu hình khởi động cùng Windows với working directory tường minh.

---

## [1.0.0] - 2026-10-06

### Added
- Tính năng dịch văn bản bôi đen qua phím tắt mặc định `Alt + D`.
- Cơ chế bảo toàn và khôi phục nội dung Clipboard người dùng.
- Tính năng dịch vùng chụp màn hình qua Windows Media OCR (`Alt + Shift + D`).
- Giao diện Popup Dark mode bo góc tự định vị thông minh gần con trỏ chuột.
- Các nút chức năng trên Popup: Ghim (Pin), Sao chép (Copy), Đóng tự động khi mất focus.
- Biểu tượng khay hệ thống (System Tray) quản lý cấu hình và thoát ứng dụng.
- Lưu trữ cấu hình người dùng tại `~/.fast_translate/config.json`.
- Script khởi động chạy ngầm `fast_translate.vbs` và `run.bat`.
