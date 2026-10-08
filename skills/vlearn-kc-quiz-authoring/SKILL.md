---
name: vlearn-kc-quiz-authoring
description: Biên soạn hoặc sửa KC/Quiz từ slide/PDF theo học phần và context đang học; phục hồi nguồn khó đọc, review nội dung và xuất ZIP VLearn hai file song ngữ kc.json, quiz.json. Dùng cho soạn học liệu và bộ câu theo phạm vi bài học, không xây portal.
---

# VLearn KC & Quiz Authoring

Biên soạn bằng agent đang làm việc. Script chỉ kiểm và đóng gói; không sinh nội dung, tự dịch, cắt bớt rubric hay chuyển schema cũ bằng cách đổi tên trường.

## Nguồn và định danh

Đọc [contract.md](references/contract.md) trước khi soạn đầu ra. Chốt PDF nguồn, checksum, số trang, vai trò tài liệu chính/tham khảo, course và mapping Day. Phân biệt `source_day` trong corpus với `learning_day_number` toàn khóa. Không suy cohort/track/Day từ tên file, thứ tự UI hoặc khóa COMP cũ. Có thể soạn nội dung khi mapping chưa xác minh; ghi rõ chưa sẵn sàng import vào đích.

## Biên soạn

Đọc [authoring.md](references/authoring.md) khi đọc nguồn hoặc sửa chất lượng nội dung.

Khi nguồn khó đọc, dùng [recovery.md](references/recovery.md): thử phục hồi phù hợp, đối chiếu lại và ghi phần còn thiếu cùng tác động tới KC/câu. Không dừng ở nhãn unreadable hoặc tự đoán dữ kiện.

Khi yêu cầu tạo/chọn quiz theo đoạn đang học, đọc [context.md](references/context.md). Nhận context tự nhiên, xác định learning unit nhỏ, mục tiêu, kiến thức đã/chưa học và prerequisite. Learning unit không mặc định trùng group KC hoặc module delivery. Ghi giả định ảnh hưởng đến phạm vi; không bắt người dùng điền ID/JSON. Soạn hoặc chọn câu theo context, giữ sidecar ngoài ZIP.

- Giữ nguồn gốc; đọc toàn bộ trang và các hình/bảng/sơ đồ có ý nghĩa. Lưu Extraction và ghi chú trang ở thư mục làm việc ngoài ZIP.
- Tách KC theo năng lực quan sát được, không theo số slide. Liên kết group → leaf KC → module/assessment slot → question. Không đặt quota KC/câu hỏi.
- Soạn trực tiếp payload VLearn. KC, blueprint và Quiz phải đủ liên kết, bằng chứng nguồn, gợi ý, đáp án/lời giải và rubric nếu cần. Ví dụ kỹ thuật ở [examples](references/examples/) chỉ minh họa cấu trúc, không phải học liệu hay quy định số lượng.
- Soạn VI/EN có cùng định danh và hợp đồng chấm điểm; duyệt tương đương nghĩa. Không điền tiếng Việt vào EN để vượt kiểm.
- Giữ nội dung học thuật khi runtime chưa hỗ trợ: ghi blocker theo loại câu/feature/grader, không âm thầm biến tự luận thành trắc nghiệm.

Trước khi giao câu/bộ học liệu, dùng [academic-review.md](references/academic-review.md) để giải câu, kiểm nguồn/phạm vi/alternative/hint/rubric và VI–EN. Sửa lỗi tại stage gốc và kiểm lại phần phụ thuộc. Tự review không được ghi là independent approval.

## Kiểm và giao

Chạy từ bất kỳ repo nội dung nào, thay `<skill>` bằng thư mục skill này:

```sh
python3 <skill>/scripts/package_day.py --kc <day>/kc.json --quiz <day>/quiz.json --out <new-delivery-directory>
```

Thêm `--target <target-evidence.json>` nếu đã đọc mapping từ môi trường đích; cấu trúc ở contract. Không có `--out` thì chỉ kiểm. Thư mục đầu ra phải mới; script không ghi đè. ZIP có đúng hai file ở gốc, giữ nguyên byte đầu vào. Báo cáo nằm ngoài ZIP.

Với quiz theo context, chạy `scripts/context_plan.py --kc <day>/kc.json --quiz <day>/quiz.json --context <day>/authoring-context.json`. Đây là kiểm phạm vi theo khai báo và candidate pool, không tự sinh câu hoặc chứng nhận chất lượng học thuật. Thiếu câu phù hợp thì báo shortage và biên soạn bổ sung trong phạm vi; không nới phạm vi/nhân bản để đủ số. Plan không thay bank hoặc slot graph.

Phân biệt bốn mức: kiểm cấu trúc local; khớp mapping đã cung cấp; preview thật trên môi trường đích; duyệt nội dung học thuật. Script chỉ chứng minh hai mức đầu, với backend revision được ghim trong báo cáo. Đọc [acceptance.md](references/acceptance.md) trước khi tuyên bố import-ready hoặc nghiệm thu.

Một bộ câu đã xuất bản phục vụ Quiz cuối Day, Ôn chỗ hay sai, Luyện tổng hợp và Thi thử; không tạo bốn ZIP cho bốn trải nghiệm. Giao nguồn/Extraction, hai JSON, ZIP, báo cáo kiểm và vấn đề còn mở. Import nháp, publish hoặc sửa mapping chỉ khi được người dùng giao thực hiện.
