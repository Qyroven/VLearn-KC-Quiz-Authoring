# Contract đầu ra VLearn

## Authority và giới hạn

Mã kiểm backend được ghim nguyên byte trong `scripts/vendor/`, commit và SHA-256 ở `provenance.json`. Loader chỉ sửa import trong AST để bỏ dependency type annotation `Settings` và nối shared error; không sửa thuật toán. Script chạy `expand_pair`, `validate_content_graph` cho cả VI/EN, và `verify_pair_target` khi có evidence. Các safeguard bổ sung của authoring được tách riêng trong report. Đây không phải toàn bộ API preview/publish hoặc schema học thuật đầy đủ.

Trước đợt import mới, đối chiếu revision backend thực tế. Khi contract đổi, cập nhật cả vendor, provenance, hướng dẫn và regression tests; không sửa vendor để ép dữ liệu qua kiểm. Xem mã nguồn gốc tại repository/commit trong provenance. Fixture examples là dữ liệu tổng hợp chính thức tại commit đó; status triển khai trong tài liệu cũ không chứng minh production hiện tại.

## Hai file trong ZIP

| File | Trường gốc chính xác |
|---|---|
| `kc.json` | `schema_version`, `day`, `package`, `localizations` |
| `quiz.json` | `schema_version`, `day`, `blueprint`, `localizations` |

- Schema gốc: `kc-quiz-kc.v2` và `kc-quiz-quiz.v2`.
- `day` giống nhau, dạng `dayNN`, bằng `learning_day_number` được zero-pad.
- `localizations` có đúng `vi` và `en`; payload có `day`, `language`, schema tương ứng `knowledge-components.day.v2` / `quiz-bank.day.v2`.
- KC: `groups` với `group_id`, `name`, `leaf_kc_ids`; `leaf_kcs` với `kc_id`, `group_id`, `name`, `knowledge`, `observable_claim`, `source_refs`; `integrated_activities` giữ hoạt động phối hợp nhiều KC nếu có.
- Quiz `blueprint` cũng có `vi` và `en`. Mỗi blueprint chứa `day`, `modules`, `assessment_slots`. Module: `module_id`, `leaf_kc_ids`, `assessment_slot_ids`, `initial_representative_slot_ids`. Slot: `slot_id`, `module_id`, `kc_id`, `variant_question_ids`.
- Mỗi question có `question_id`, `question_version`, `module_id`, `primary_kc_id`, `contributing_kc_ids`, `assessment_slot_ids`, `variant_family_id`, `role`, `cognitive_operation`, `estimated_difficulty`, `grading_method`, `max_points`, `interaction`, `answer_key_or_rubric`, `answer_explanation`, `source_refs`; thêm hints và trường học thuật có nghĩa ở payload, không thêm trường gốc.

Đây là mô tả trường và example thực thi được, không phải JSON Schema exhaustive. Xem ví dụ nguyên bản [kc.json](examples/kc.json), [quiz.json](examples/quiz.json). Không sao chép nội dung/định danh synthetic làm hàng thật.

### Package

`package_id`, `course_key` là metadata truy vết; không xác định đích import. Bắt buộc `traceability`, `revisions`, `curriculum_decisions`, `curriculum_identity`:

```json
{"intake":"K04","level":"L34","phase":2,"track":1,"source_day":"day16","learning_day_number":16}
```

Ví dụ trên chỉ minh họa, không xác nhận mapping thật. Identity có đúng sáu trường. `intake` KNN, `level` LNN, phase số nguyên 1–9, track 0–9, learning day 1–99. Không dùng vị trí thứ nhất trên UI để kết luận Day toàn khóa là 1.

`materials` tham chiếu nguồn ngoài ZIP: mỗi bản ghi `material_id`, `label`, `type`, `primary`, `sha256`, `page_count` theo nguồn thực; không có `file` trỏ PDF nhúng. Checksum phải được tính từ file thật. Local report chỉ kiểm khai báo, không xác minh byte PDF. Dùng `traceability.source_mappings` gồm `{extraction_path, material_id}`; mọi nguồn không nằm trong inventory khai báo trong `unbundled_source_refs` với `extraction_path` và lý do. KC/câu tham chiếu `{extraction_path, page}`; page tính từ 1. Không xóa source refs để né lỗi.

`revisions` lưu revision KC/Quiz; `curriculum_decisions` ghi quyết định `is_core`/`placement` và phần chưa chốt. Không tự tuyên bố được duyệt trong `review` chỉ vì script pass. Không tự tạo các trường reserved `files`, `content`, `counts`, `languages`, `day`, `schema_version`, `source_format`, `pair_blueprint_en` trong package; backend sinh nội bộ.

### Interaction và đáp án

| `interaction.type` | Dữ liệu tương tác | `answer_key_or_rubric` |
|---|---|---|
| `single_select` | `choices[{choice_id,text}]` | `correct_choice_id` |
| `multi_select` | `choices[{choice_id,text}]` | `correct_choice_ids` |
| `matching` | `left/right[{id,text}]` | `correct_pairs` map left ID → right ID |
| `ordering` | `options[{option_id,text}]` | `correct_order` là permutation đầy đủ |
| `numeric_input` | `required_unit` | `value`, `tolerance` ≥ 0, `unit` khớp |
| `short_text` | `prompt` | `exemplar_answer`, `criteria[{criterion_id,description,points}]`; tổng points = max_points |

Tất cả interaction có prompt độc lập, đủ đề bài. Giữ `grading`, `accept_equivalent_wording`, `allowed_scores`, `score_policy` nếu có theo contract runtime đã xác minh; không tự phát minh enum/đặt field tuỳ ý rồi coi là hỗ trợ. Example hiện dùng `objective_key`, `initial_check`/`reassessment`, `Apply`, `easy`; xác minh policy/runtime cho lựa chọn khác. Chấp nhận import không chứng minh grader AI đã hoạt động.

VI/EN cùng IDs, liên kết, role, interaction, số điểm và answer key. Prose được dịch; danh sách diễn giải có thể khác số đoạn. Không đổi criterion ID hay điểm khi dịch rubric. Hint không chứa đáp án hoặc phần năng lực cần đo.

## Target evidence ngoài ZIP

Read-only evidence từ môi trường đích:

```json
{
  "environment":"https://vlearn.dev",
  "observed_at":"<actual timestamp>",
  "course_id":"<actual course ID>",
  "mapping":{"course_id":"<same ID>","intake":"K04","level":"L34","phase":2,"track":1},
  "target_day":{"day_code":"<actual destination day_code>"},
  "source_days":[{"course_id":"<same ID>","source_day":"day16","learning_day_number":16,"target_day_code":"<actual destination day_code>"}]
}
```

Lấy mapping bằng `GET /courses/{course_id}/authoring/kc-quiz-packages/source-mapping`, `GET .../source-days`, và Day đích thật. Lưu provenance/timestamp; không đưa cookie/key vào evidence. Script kiểm sự khớp với dữ liệu cung cấp, không tự xác thực evidence hay truy cập server. Sai/thiếu mapping thì báo blocker cho admin; ZIP không sửa được mapping. Day gộp/shared slide cần mapping đã được duyệt, không tự gộp nội dung hoặc chọn một Day tuỳ ý.
