# Review chất lượng và sửa vòng lặp

CLI tạo records pending và kiểm stale/missing evidence nằm ở [evidence-workflow.md](evidence-workflow.md). Helper kiểm ghi nhận và liên kết, không tự đọc/đánh giá chất lượng lập luận.

Review dựa trên nội dung thực tế. Lưu findings theo ID và nguồn, không thay bằng score tổng hoặc checklist đã tick.

| Mức kiểm | Câu hỏi cần trả lời | Khi fail |
|---|---|---|
| Nguồn → Extraction | Còn đủ điều kiện, số/đơn vị, bảng/hình/code, quan hệ xuyên trang không? | Sửa Extraction hoặc phục hồi nguồn; kiểm downstream |
| Extraction → KC/unit | Có năng lực bị bỏ, gộp nhầm, chia quá vụn? Người học có thể đúng phần A nhưng sai B và cần luyện khác không? | Sửa ranh giới và coverage; giữ lý do |
| Context → Question | Đo đúng phần vừa học? Cần kiến thức chưa có? Dữ kiện bắt buộc đã trong đề chưa? | Loại khỏi bộ hiện tại hoặc viết lại; không chỉ đổi nhãn unit |
| Question → Evidence | Tự giải được bằng dữ kiện đề và kiến thức được phép? Có strong alternative đúng? | Sửa stem/answer/rubric, giải lại cả các lựa chọn |
| Hints | Định hướng bước tiếp mà không thực hiện năng lực đang đo? | Viết lại hint hoặc ghi không có hint phù hợp |
| Rubric | Tiêu chí phân biệt được phản hồi khác chất lượng, điểm nhất quán, chấp nhận tương đương đúng? | Thử đáp án đúng một phần/sai hợp lý; sửa criterion/exemplar |
| VI ↔ EN | Nghĩa, độ khó, ambiguity, đơn vị, clues và mức tiết lộ giống nhau? | Sửa bản dịch và kiểm lại answer contract |

Mỗi question có record tác nghiệp ngoài ZIP: `question_id`, source refs, lời giải kiểm độc lập với key đã viết, alternative/chống ví dụ đã xét, kiểm prerequisite theo context, hint leakage, rubric trial khi cần, VI/EN findings và kết luận `needs_revision`/`self_reviewed`. Ghi reviewer và timestamp thật; không tự gắn `independently_approved` cho self-review.

Với câu selection, đọc các distractor như học viên có hiểu nhầm hợp lý. Với câu construction, kiểm đề có buộc tạo ra bằng chứng cần đo hay có thể trả lời bằng lặp lại một từ khóa. Ví dụ mục tiêu là lập luận chọn retrieval: chỉ hỏi “retrieval là gì?” chưa đo mục tiêu đó dù cùng KC tag.

Một Day cần coverage record: năng lực từ nguồn/context → unit/KC → assessment intent/slot → câu; ghi phần represented-but-unmeasured, excluded có lý do và unresolved. Có question ID cho mỗi KC không tự chứng minh coverage.

Nếu sửa câu làm thay đổi năng lực/prerequisite, cập nhật annotation, slot và context plan. Nếu sửa evidence, kiểm lại KC liên quan. Chỉ chạy lại kiểm bị ảnh hưởng và regression gate cần thiết; không lặp review toàn bộ vô hạn để tạo cảm giác chắc chắn.
