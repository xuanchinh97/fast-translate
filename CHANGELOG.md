# 📋 Changelog - FastTranslate

Mọi thay đổi đáng chú ý của dự án FastTranslate sẽ được ghi nhận tại file này.
Định dạng tuân theo [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) và phiên bản tuân theo [Semantic Versioning](https://semver.org/).

---

## [1.5.2] - 2026-10-19

### Fixed
- **Khắc phục triệt để lỗi "Chưa phát hiện văn bản bôi đen" khi bấm `Alt + D`**:
  - **Khắc phục xung đột phím tắt**: Bật cờ `suppress=True` trên hook bàn phím toàn cục để chặn `Alt + D` truyền vào các trình duyệt (Chrome, Edge, Firefox, Explorer), ngăn trình duyệt tự động nhảy con trỏ lên thanh địa chỉ (Omnibox) làm mất vùng chọn bôi đen của người dùng.
  - **Cơ chế nhả phím Modifier ảo với Hardware Scan Code**: Tự động gửi tín hiệu nhả phím ảo cho `Alt` (`VK_LMENU`/`VK_RMENU`, scan code `0x38`) và `Shift` trước khi mô phỏng `Ctrl + C`, ngăn hệ thống nhận nhầm thành tổ hợp `Alt + Ctrl + C` (vốn không có tác dụng sao chép).
  - **Theo dõi số thứ tự Clipboard (`GetClipboardSequenceNumber`)**: Loại bỏ hoàn toàn thao tác xóa trắng clipboard (`pyperclip.copy("")`) gây mất dữ liệu của người dùng; chuyển sang theo dõi sự thay đổi của sequence number trong Windows API để nhận diện văn bản mới trong <20ms.
  - **Kiến trúc trích xuất đa tầng (Multi-Tier Extraction)**:
    - *Tier 1*: Mô phỏng `Ctrl + C` nguyên tử bằng `SendInput` (có fallback `keybd_event` với phần cứng scan code).
    - *Tier 2*: Gửi trực tiếp thông điệp `WM_COPY` đến control/cửa sổ đang focus (`hwndFocus`).
    - *Tier 3*: Tự động nhận diện nội dung đã sao chép sẵn trong clipboard nếu ứng dụng đích chặn mô phỏng phím (ví dụ terminal/cửa sổ quyền Administrator).
  - **Đọc/Ghi Clipboard Unicode trực tiếp**: Tích hợp trực tiếp Windows Clipboard API (`CF_UNICODETEXT`), xử lý hoàn hảo tiếng Việt có dấu, ký tự châu Á và các ký hiệu đặc biệt mà không phụ thuộc thư viện ngoài.
  - Bổ sung bộ kiểm thử `tests/test_text_extractor.py` và cập nhật kiểm thử bằng chứng `tests/test_evidence.py` (`test_06_text_extractor_multi_tier`), toàn bộ **34/34 tests** đạt kết quả hoàn hảo.

---

## [1.5.1] - 2026-10-16

### Fixed
- **Sửa lỗi tính năng phát âm (TTS) cho văn bản gốc tiếng Anh**:
  - Khắc phục sự cố nút `🔊 Đọc` không phát ra tiếng khi văn bản gốc là tiếng Anh do lỗi không tương thích của bộ tổng hợp giọng `QTextToSpeech/WinRT` trên Windows.
  - Chuyển sang sử dụng bộ phát âm chất lượng cao chuẩn bản ngữ (Google TTS) kết hợp trình phát âm thanh Windows MCI (`winmm.dll`) cho tất cả ngôn ngữ bao gồm tiếng Anh.
  - Tích hợp chuẩn hóa đường dẫn ngắn 8.3 (`GetShortPathNameW`) giúp MCI phát âm thanh ổn định tuyệt đối trên mọi tên tài khoản Windows (kể cả có dấu tiếng Việt, dấu cách hoặc ký tự đặc biệt).
  - Tự động lưu cache âm thanh tại `~/.fast_translate/tts_cache/` giúp các lần nghe sau phát tức thì (0ms) ngay cả khi không có mạng.
  - Bổ sung cơ chế dự phòng ngoại tuyến (Offline Fallback) qua Windows SAPI.
  - Bổ sung unit test `test_speak_english_source_caching` trong `tests/test_tts_and_swap.py`.

---

## [1.5.0] - 2026-10-13

### Added
- **🚀 Đóng gói file thực thi độc lập (Standalone Packaging - FastTranslate.exe)**:
  - Cấu hình file build spec `FastTranslate.spec` với đầy đủ dependencies (`PySide6`, `winocr`, `winrt`, `PIL`, `pynput`, `deep_translator`...).
  - Tạo script **`build.bat`** hỗ trợ đóng gói tự động thành 1 file duy nhất `dist/FastTranslate.exe`.
  - Chạy ngay lập tức trên mọi máy tính Windows mà **không cần cài đặt Python, môi trường ảo (.venv) hay thư viện ngoài**.
  - Tích hợp chuẩn hóa `sys.frozen` và `sys._MEIPASS` cho icon độ phân giải cao, khởi động cùng Windows (Registry Run trỏ trực tiếp vào exe) và lưu vết log an toàn tại `~/.fast_translate/app.log`.
  - Chạy ở chế độ Windowed không hiển thị cửa sổ console đen (`console=False`), tối ưu dung lượng và tốc độ khởi chạy.

---

## [1.4.0] - 2026-10-13

### Added
- **⚙️ Giao diện Cài đặt trực quan (Settings Dialog)**:
  - Thêm mục menu **`⚙️ Cài đặt...`** trực tiếp trong khay hệ thống (System Tray).
  - Hỗ trợ đổi phím tắt trực quan: người dùng chỉ cần click vào ô nhập rồi bấm tổ hợp phím mong muốn (hỗ trợ phím Modifiers Ctrl/Alt/Shift/Win, bấm `Esc` để hủy, `Backspace/Delete` để xóa).
  - Chọn ngôn ngữ nguồn/đích mặc định từ danh sách trực quan.
  - Tùy chọn hệ thống: Khởi động cùng Windows, Tự đóng popup khi mất focus, Tự khôi phục clipboard cũ.
  - Nút **`↺ Đặt lại mặc định`** đưa mọi thiết lập về cấu hình tiêu chuẩn ban đầu.
  - Áp dụng phím tắt mới tức thì (`reload hotkeys`) mà **không cần khởi động lại ứng dụng**, đồng thời cập nhật menu khay hệ thống và thông báo toast xác nhận.
- **🖼️ Tiền xử lý ảnh OCR đa tầng (OCR Image Preprocessing)**:
  - Tự động phóng to thông minh (Upscale bằng thuật toán LANCZOS) với các vùng chụp nhỏ dưới ngưỡng nhận diện.
  - Chuyển đổi ảnh đa cấp xám (Grayscale) và cân bằng độ tương phản tự động (Auto-contrast).
  - Cơ chế nhận diện đa tầng (Multi-pass recognition): thử nghiệm ảnh gốc, ảnh tăng cường tương phản, và ảnh đảo màu phân cực (Inverted polarity).
  - Khắc phục triệt để vấn đề nhận diện chữ trên nền tối (Dark mode), chữ trắng trên nền đen/xám và giao diện IDE code.
- Bộ kiểm thử tự động `tests/test_settings_dialog.py` và kiểm thử bổ sung cho OCR dark mode trong `tests/test_ocr.py`.

---

## [1.3.0] - 2026-10-13

### Added
- **Phát âm âm thanh đa ngôn ngữ (Text-to-Speech - TTS 🔊)**:
  - Nút `🔊 Đọc` văn bản gốc trên thanh công cụ để nghe phát âm từ vựng/câu tiếng Anh chuẩn.
  - Nút `🔊 Đọc` bản dịch ở góc dưới để nghe phát âm của kết quả dịch.
  - Tích hợp giọng đọc nội tại Windows qua `QTextToSpeech` (offline, 0ms latency cho tiếng Anh) kết hợp bộ phát âm trực tuyến và bộ đệm cache âm thanh `~/.fast_translate/tts_cache/`.
  - Tự động dừng phát âm khi người dùng đóng/ẩn popup.
- **Đổi chiều ngôn ngữ (Language Swap ⇄)**:
  - Nút **`⇄`** trên thanh tiêu đề cho phép hoán đổi nhanh chiều dịch (ví dụ `AUTO ➔ VI` ⇄ `VI ➔ EN`).
  - Tự động hoán đổi nội dung giữa ô gốc và ô dịch nếu đã có sẵn bản dịch.
- **Chọn cặp ngôn ngữ linh hoạt**:
  - Badge ngôn ngữ có thể click để mở menu chọn nhanh các cặp ngôn ngữ phổ biến: Tiếng Anh, Tiếng Việt, Tiếng Nhật, Tiếng Hàn, Tiếng Trung, Tiếng Pháp.
- Bộ kiểm thử tự động `tests/test_tts_and_swap.py`.

### Changed
- **Tinh gọn thanh công cụ**: Chuyển nút dịch thủ công thành **`↻ Thử lại`** (Retry), mặc định ẩn đi trong trạng thái bình thường và chỉ tự động hiển thị nổi bật khi bản dịch gặp sự cố kết nối/timeout.

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
