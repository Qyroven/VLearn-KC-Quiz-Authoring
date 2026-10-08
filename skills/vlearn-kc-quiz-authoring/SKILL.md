---
name: vlearn-kc-quiz-authoring
description: Biên soạn hoặc sửa KC và Quiz từ slide/PDF cùng ngữ cảnh giảng viên, xuất ZIP VLearn hai file kc.json và quiz.json có VI/EN, kiểm liên kết và đối chiếu course/Day. Dùng khi chuẩn bị nội dung để import VLearn; không phải skill xây portal luyện tập.
---

# VLearn KC & Quiz Authoring

Biên soạn bằng agent đang làm việc. Script chỉ kiểm và đóng gói; không sinh nội dung, tự dịch, cắt bớt rubric hay chuyển schema cũ bằng cách đổi tên trường.

## Nguồn và định danh

Đọc [contract.md](references/contract.md) trước khi soạn đầu ra. Chốt PDF nguồn, checksum, số trang, vai trò tài liệu chính/tham khảo, course và mapping Day. Phân biệt `source_day` trong corpus với `learning_day_number` toàn khóa. Không suy cohort/track/Day từ tên file, thứ tự UI hoặc khóa COMP cũ. Có thể soạn nội dung khi mapping chưa xác minh; ghi rõ chưa sẵn sàng import vào đích.

## Biên soạn

Đọc [authoring.md](references/authoring.md) khi đọc nguồn hoặc sửa chất lượng nội dung.

- Giữ nguồn gốc; đọc toàn bộ trang và các hình/bảng/sơ đồ có ý nghĩa. Lưu Extraction và ghi chú trang ở thư mục làm việc ngoài ZIP.
- Tách KC theo năng lực quan sát được, không theo số slide. Liên kết group → leaf KC → module/assessment slot → question. Không đặt quota KC/câu hỏi.
- Soạn trực tiếp payload VLearn. KC, blueprint và Quiz phải đủ liên kết, bằng chứng nguồn, gợi ý, đáp án/lời giải và rubric nếu cần. Ví dụ kỹ thuật ở [examples](references/examples/) chỉ minh họa cấu trúc, không phải học liệu hay quy định số lượng.
- Soạn VI/EN có cùng định danh và hợp đồng chấm điểm; duyệt tương đương nghĩa. Không điền tiếng Việt vào EN để vượt kiểm.
- Giữ nội dung học thuật khi runtime chưa hỗ trợ: ghi blocker theo loại câu/feature/grader, không âm thầm biến tự luận thành trắc nghiệm.

## Kiểm và giao

Chạy từ bất kỳ repo nội dung nào, thay `<skill>` bằng thư mục skill này:

```sh
python3 <skill>/scripts/package_day.py --kc <day>/kc.json --quiz <day>/quiz.json --out <new-delivery-directory>
```

Thêm `--target <target-evidence.json>` nếu đã đọc mapping từ môi trường đích; cấu trúc ở contract. Không có `--out` thì chỉ kiểm. Thư mục đầu ra phải mới; script không ghi đè. ZIP có đúng hai file ở gốc, giữ nguyên byte đầu vào. Báo cáo nằm ngoài ZIP.

Phân biệt bốn mức: kiểm cấu trúc local; khớp mapping đã cung cấp; preview thật trên môi trường đích; duyệt nội dung học thuật. Script chỉ chứng minh hai mức đầu, với backend revision được ghim trong báo cáo. Đọc [acceptance.md](references/acceptance.md) trước khi tuyên bố import-ready hoặc nghiệm thu.

Một bộ câu đã xuất bản phục vụ Quiz cuối Day, Ôn chỗ hay sai, Luyện tổng hợp và Thi thử; không tạo bốn ZIP cho bốn trải nghiệm. Giao nguồn/Extraction, hai JSON, ZIP, báo cáo kiểm và vấn đề còn mở. Import nháp, publish hoặc sửa mapping chỉ khi được người dùng giao thực hiện.
