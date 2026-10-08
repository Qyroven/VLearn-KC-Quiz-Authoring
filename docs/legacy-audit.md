# Audit bản cũ — 2026-10-09

Phạm vi đọc: repo Qyroven/KC-Quiz-Mastery tại commit `3c87e58568819c9f0dd55aa00da13c2e8b3ee297`; instructions, session workflow, KC/Quiz contracts, ví dụ neutral/adaptive và exporter Learning. Đây là audit thiết kế và mã, chưa phải đánh giá chất lượng một Day Phase 2 do bản cũ sinh.

## Giữ / sửa / bỏ khỏi phạm vi mới

| Phần | Bằng chứng trong repo cũ | Quyết định |
|---|---|---|
| Đọc nguồn multimodal | `skills/learning-authoring-pipeline/SKILL.md:28–36`; `references/session-workflow.md`, mục Extraction: đọc mọi trang, giữ điều kiện, quan hệ hình, page_note, uncertainty | **Giữ**; không có bằng chứng để nói bản cũ chỉ đọc text hoặc không hiểu hình. |
| Phục hồi nguồn | `SKILL.md:51–52` yêu cầu tiếp tục phần đủ bằng chứng khi không phục hồi được; có OCR/render hỗ trợ nhưng entrypoint chưa định nghĩa attempt → verify → impact → request cụ thể | **Sửa** bằng recovery record, cách kiểm lại và tiêu chí dừng theo dữ kiện, không chỉ nhãn unreadable. |
| Tách KC | `session-workflow.md`, mục Shared KC, dùng contrasting learner responses và nhu cầu remediation; ví dụ `prompts/kc-v1/examples-v1/independent-capabilities.json` giữ hai năng lực riêng | **Giữ** nguyên tắc độc lập; thêm learning unit đủ nhỏ và mapping tới KC/blueprint. Không coi mọi group cũ là sai. |
| Context giảng viên | `quiz_contracts.py:87–106`, `:433`, `:825–836` có context evidence/ref/hash và kiểm thuộc KC | **Giữ** provenance. Nhận định “bản cũ không có context” là không chính xác. **Bổ sung** vị trí đang học, kiến thức sẵn có, chưa học và mục đích hỏi; đó khác context làm bằng chứng chuyên môn. |
| Quiz có slot/variant | `quiz_contracts.py:118–131`; `prompts/quiz-v1/examples-v3/adaptive-slot-with-hint.json` có intent, slot, variants, hints | **Giữ** evidence intent; không phát minh lại slot, không áp quota. Bổ sung chọn câu theo learning unit và prerequisite hiện có. |
| Format Quiz | `quiz_contracts.py:27` dùng `quiz-batch.v3`; ví dụ dùng `interaction` chuỗi, `kc_id`, `correct_answer`/rubric riêng | **Thay delivery contract** bằng payload VLearn native: `interaction` object, `primary_kc_id`, `answer_key_or_rubric`, blueprint song ngữ. Đổi tên trường đơn giản không đủ. |
| Exporter Learning | `product/learning.py:36`, `:73–77`, `:165`: `learning-package.v1`, numeric bị từ chối ở exporter, `practice_only: true` | **Bỏ khỏi phạm vi mới** portal/exporter/scorer đó. Đây là giới hạn runtime của exporter cũ, không phải bằng chứng numeric không soạn được. |
| Semantic review | `session-workflow.md`, mục Quiz; `SKILL.md:40–50`: solve/check, không mất dữ kiện trong hint, schema pass không đồng nghĩa approved | **Giữ và cụ thể hóa** bằng review từng câu và phụ thuộc nguồn, phạm vi, rubric, bản dịch. |

## Điều chưa thể kết luận từ audit này

- Không có kết quả thử Day thật để kết luận bản mới biên soạn tốt hơn bản cũ.
- Ví dụ trong repo cũ là worked examples, không phải nội dung production hay kết quả sinh gần đây.
- Mã kiểm mới chứng minh contract và tính nhất quán khai báo; chưa chứng minh OCR đúng, module hợp lý hoặc câu đo đúng KC.

Thiết kế và implementation mới ở [rebuild-design.md](rebuild-design.md). Nguồn audit có thể mở theo commit tại https://github.com/Qyroven/KC-Quiz-Mastery/tree/3c87e58568819c9f0dd55aa00da13c2e8b3ee297/skills/learning-authoring-pipeline .
