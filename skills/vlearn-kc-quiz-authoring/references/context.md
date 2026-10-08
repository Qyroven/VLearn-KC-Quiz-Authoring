# Quiz theo học phần và context đang học

## Nhận yêu cầu tự nhiên

Ví dụ: “Vừa xong chunking ở trang 12–18, đã biết embedding, chưa học reranking; tạo câu kiểm tra nhanh trước khi sang retrieval.” Agent đọc nguồn và bank để nhận diện unit/KC thật, ghi giả định nếu chỉ có tên gần đúng. Không yêu cầu người dùng thuộc ID hoặc tự viết JSON.

Vị trí trang chỉ hỗ trợ định vị; không tự chứng minh học viên đã học mọi kiến thức trang trước. Context giảng viên làm bằng chứng chuyên môn cần attribution riêng với context điều khiển việc ra câu.

## Learning units

Chia theo mục tiêu nhỏ có thể dạy/kiểm lại: title, goal, KC IDs, prerequisite IDs và source windows. Unit không mặc định một slide hoặc một Day. Khi một KC xuất hiện ở nhiều unit, annotation câu cần chỉ rõ unit và công việc đo; lọc theo KC đơn thuần không đủ tránh hỏi phần chưa dạy. Câu tích hợp được gắn nhiều unit/KC; không ép thành một KC cho tiện chọn.

## Sidecar `authoring-context.v1`

Ở ngoài ZIP, dùng khi đã có KC/Quiz hoặc chuẩn bị kiểm bộ vừa soạn. Ví dụ kỹ thuật thực thi được ở [context.json](examples/context.json), gắn với hai bank synthetic bên cạnh.

- `request`: `purpose` (`inline_check`, `end_of_day`, `weak_spots`, `mixed_practice`, `mock_exam`), `free_text`, `position` tuỳ ngữ cảnh, `unit_ids`, `target_kc_ids` (tuỳ chọn), `available_kc_ids`, `excluded_kc_ids`, `question_count`/`time_minutes` (tuỳ chọn), `assumptions`.
- `units`: `{unit_id,title,goal,kc_ids,prerequisite_kc_ids,source_windows,blueprint_module_ids}`. `source_windows` mô tả nguồn/trang, không xác nhận đã đọc. `blueprint_module_ids` mapping delivery, không buộc 1:1 với unit.
- `question_annotations`: `{question_id,unit_ids,requires_kc_ids}`. `requires_kc_ids` khai báo đủ prerequisite để giải; KC đang đo lấy từ bank, không copy hoặc thay đáp án sang sidecar.
- `open_source_gaps`: `{issue_id,affected_kc_ids,affected_question_ids}` chỉ những gap chưa giải quyết. Đóng gap dựa trên recovery record rồi cập nhật context.

`available_kc_ids` là kiến thức có thể dùng ở thời điểm hỏi, gồm phần vừa học xong. Prerequisite ngoài Day được dùng ID nhất quán trong context; không cần chèn KC giả vào bank Day. `excluded_kc_ids` thắng mọi lựa chọn khác. Các trường quyết định phạm vi có lỗi chính tả bị từ chối, không âm thầm bỏ qua.

## Chọn hoặc sinh câu

```sh
python3 <skill>/scripts/context_plan.py --kc <day>/kc.json --quiz <day>/quiz.json --context <day>/authoring-context.json
```

Script kiểm bank bằng packager và trả candidate IDs/reasons; không thay bank, không sinh câu hay cho academic approval. Câu eligible khi mọi unit gắn câu nằm trong unit được chọn, mọi KC đo nằm trong target scope và available, prerequisite có sẵn, không bị excluded/gap nguồn. Annotation thiếu → chưa xác minh, không eligible.

Agent chọn bộ cuối theo mục tiêu và assessment slot, tránh các variant trùng công việc trong cùng lượt. Thiếu câu phù hợp thì soạn bổ sung từ nguồn trong phạm vi, giải/review, cập nhật bank+blueprint+annotation và kiểm lại; không tự nới scope hoặc nhân bản câu để đủ quota. Count/time là yêu cầu thiết kế, script không suy số câu từ phút và không khẳng định làm vừa giờ.

`inline_check` là mục đích biên soạn theo đoạn học, **không phải tính năng student thứ năm đã có trên VLearn**. Export đầy đủ Day vẫn dùng hai file; plan context là artefact tác nghiệp riêng. Context không quyết định policy lộ đáp án/retry của ứng dụng; đối chiếu policy môi trường đích.
