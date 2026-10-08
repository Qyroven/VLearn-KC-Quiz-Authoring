# Giao và nghiệm thu

## Bằng chứng phải đúng phạm vi

1. **Local preflight:** chạy script, giữ report, checksum hai JSON/ZIP, backend commit. Bao gồm pair adapter và content graph chính thức được ghim, thêm authoring checks. Chưa chạy preview API, quota ZIP server, access policy, publish gate hoặc AI grader.
2. **Mapping:** đối chiếu course/Day với evidence từ đúng môi trường, đúng thời điểm. Report `matched_supplied_evidence` chỉ xác nhận khớp file evidence. Không gọi “production mapping verified” nếu chưa đọc production.
3. **Preview thật:** dùng đúng ZIP và Day trên môi trường được giao. Lưu thời điểm, môi trường, course/Day, package checksum, kết quả hoặc error code. Không suy từ test fixture/local backend thành production pass.
4. **Duyệt học thuật:** đọc lại nguồn, KC/slot coverage, VI/EN, solve/rubric/hints và các giới hạn còn mở. Technical pass không thay thế review.

Khi được giao test full, test import → preview thay đổi → nhập nháp → sửa/lưu → thử học viên → hoàn tất duyệt → diff/xác nhận publish. Test lịch sử/tạo nháp từ bản cũ, live/draft separation và lượt cũ giữ pin. Gỡ publish cần được giao cụ thể nếu ảnh hưởng học viên thật.

Student: Quiz cuối Day mở đúng Day; Ôn chỗ hay sai dùng lịch sử sai; Luyện tổng hợp dùng Day/số câu đã chọn; Thi thử dùng thời gian, nộp/xem kết quả đúng policy. Kiểm không lộ đáp án/lời giải khi chưa được phép, refresh/Back/tiếp tục và tạo lượt mới. Không coi cả bốn trải nghiệm đạt chỉ vì import thành công. Dùng dữ liệu thử/phạm vi người dùng cho phép, ghi rõ các bước chưa kiểm.

Giao mỗi Day gồm hai JSON, ZIP, report và đường dẫn nguồn/Extraction/review ngoài ZIP. Báo blocker nếu nguồn/mapping/grader chưa đủ. Không đóng issue hoặc tuyên bố nghiệm thu dựa riêng vào script pass.
