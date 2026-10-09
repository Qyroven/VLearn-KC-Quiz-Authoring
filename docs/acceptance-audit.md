# Nghiệm thu bước 3–5 — 2026-10-09

Controller độc lập với người triển khai. Phạm vi: công cụ và quy trình phục hồi nguồn, tổ chức học phần/KC/Quiz theo context, review học thuật. Không nghiệm thu toàn bộ Day Phase 2 hoặc môi trường VLearn qua test local.

## Tiêu chí trước khi đối chiếu kết quả

| Bước | Tiêu chí có thể kiểm thực thi | Bằng chứng tối thiểu |
|---|---|---|
| 3. Phục hồi nguồn | Có thao tác thật tạo artefact từ nguồn; trang/vùng/input/provenance được ghi; dữ kiện chưa xác minh không tự trở thành recovered | Lệnh chạy, input hash, ảnh/text/output, recovery record và negative cases |
| 3. Ảnh hưởng downstream | Gap chưa đóng giữ tác động KC/câu, yêu cầu bổ sung đúng dữ kiện; phục hồi mới cần recheck | Record open/resolved, context loại câu bị ảnh hưởng, không chỉ nhãn unreadable |
| 4. Học phần và KC | Unit nhỏ có mục tiêu/prerequisite/nguồn và lý do ranh giới; unit không ép bằng module delivery | Worked evidence có contrasting learner responses và coverage |
| 4. Quiz theo context | Cùng kho, context đối lập cho candidate pool khác hợp lý; thiếu annotation/prerequisite/nguồn thì bị loại; thiếu câu không tự nới scope | Report theo question ID, nguyên nhân loại, shortage, source/question input hashes |
| 5. Review | Review gắn nội dung/version/hash hiện tại, lời giải/alternative/hint/rubric/bilingual; open finding hoặc stale review chặn ready | Review records và positive/negative/stale cases |
| 5. Độc lập | Tự review không được gọi independent approval; structural pass không chứng minh lời giải đúng | Reviewer identity, verdict rõ, báo cáo giới hạn |

## Trạng thái tại thời điểm bắt đầu

Baseline chỉ có instructions recovery/review và `context_plan.py`; chưa có công cụ phục hồi hoặc record validator cho bước 3/5. Bản thiết kế đã nói rõ chưa thực hiện pilot Day thật. Các test packager/context baseline không chứng minh OCR đúng, module hợp lý hay học liệu ready.

## Đối chiếu cuối

Kết luận: **chấp nhận implementation bước 3–5 và trial giới hạn trên nguồn thật** theo bằng chứng bên dưới. Không đồng nghĩa hoàn thành toàn bộ rebuild/pilot Day hoặc import-ready trên VLearn.

### Bằng chứng nguồn thật đã đọc độc lập

Controller đã mở ảnh `handoff/vlearn-rebuild-step3-5-20261009/checker/first-principles-page-16.png` và đối chiếu `real-source-recovery-and-review.json`:

- Trục X từ chắc chắn sang bất định; trục Y tác động tăng lên trên; vùng vàng “đào trước” chứa hai giả định gặp mặt/xác minh và khách đến văn phòng.
- Footer in số 17 nhưng vị trí PDF là trang 16; record phân biệt hai số.
- Slide ghi rõ các giả định Wise chỉ là ví dụ minh họa; không được đổi thành dữ kiện lịch sử.
- Không có thang số định lượng; câu yêu cầu tính điểm ưu tiên bị bác và đổi sang so sánh định tính có điều kiện “theo nguyên tắc trên slide”.
- Hint đầu tiết lộ toàn đáp án bị phát hiện; hint sửa chỉ hướng so sánh hai trục. Ba phản hồi giả lập kiểm mức 0/1/2 làm rõ rubric thử nghiệm.

Kết luận giới hạn: có trial thực tế về phục hồi quan hệ hình và sửa câu/hint/rubric, không chỉ checklist. Đây là slice một trang được checker tự soạn và self-review; không phải kiểm đủ 21 trang, toàn Day, independent approval học liệu root hay runtime AI rubric.


### Outcomes đối chiếu cuối

| Tiêu chí | Kết quả cụ thể | Nhận định |
|---|---|---|
| Phục hồi nguồn thực thi | `source_workbench.py` prepare/recover tạo render/text/attempt có hash và source inventory. Checker chạy trên PDF First Principles thật trang 16; root prepare đủ ba trang reference Interviews. PDFplumber fallback chạy thật. | Đạt mechanics và trial nguồn thật; OCR không tự được gắn verified. |
| Recovery bounds/provenance | Checker tìm crop ngoài trang được chấp nhận sai; implement đã sửa, negative rerun và regression pass. File đổi hash bị chặn; output có sẵn không ghi đè. | Defect phát hiện đã sửa. |
| Học phần nhỏ | Reference Interviews có hai unit/KC: hỏi về hành vi đã xảy ra; xác định pain ưu tiên từ bằng chứng và giới hạn kết luận. Có boundary argument phản hồi đối lập, không chỉ đổi nhãn. | Có worked reasoning thực tế; chưa có learner outcome để xác nhận ranh giới tối ưu. |
| Quiz theo context | Cùng bank ba câu: inline chỉ eligible hai câu behavior, q-priority bị loại; cả hai unit eligible ba câu; controlled open priority gap loại q-priority. | Đạt graph/context mechanics và case đối lập. Không có feature VLearn tự chọn theo slide được chứng minh. |
| Review thực thi | `authoring_evidence.py` scaffold/check gắn hashes KC/Quiz/context/Extraction; bao phủ trang và từng KC/câu; open finding, stale review, citation chỉ vào excluded page đều bị chặn. | Đạt consistency gate, không tự xác minh nội dung lời review. |
| Independent review trial | Checker đọc ba trang render và giải riêng ba câu VI/EN. Phát hiện minor rubric “recent” vs “most recent”; root sửa cả hai ngôn ngữ, nâng question_version lên 2; checker cập nhật review theo hash mới. | Không còn blocker trong slice được review. |
| Hints/rubric | Pilot ba câu không có hints. Trial chart riêng phát hiện hint lộ đáp án và sửa; rubric thử correct/partial/incorrect, gồm đáp án có giả định dẫn dắt. | Có chứng cứ sửa leak và scoring trial; chưa chứng minh hiệu quả hints rộng hoặc runtime AI grader. |
| Gate regression | Controller chạy `python3 -m unittest discover -s tests -v`: 52 tests pass. Controller rerun pilot evidence đúng context: exit0, zero blockers; đổi context trong cùng evidence: exit2 `review_stale`. | Đạt tại thời điểm audit; log ở controller/tests.log. |

### Bằng chứng có thể mở

Các đường dẫn dưới đây tương đối với workspace `/Users/quyenmanh/Developer/vlearn`:

- `handoff/vlearn-rebuild-step3-5-20261009/pilot-interviews/`: nguồn ba trang đã đọc, Extraction, hai KC/unit, ba câu song ngữ, context đối lập và evidence bound inputs.
- `handoff/vlearn-rebuild-step3-5-20261009/checker/independent-pilot-review.json`: review độc lập cập nhật sau sửa rubric.
- `handoff/vlearn-rebuild-step3-5-20261009/checker/adversarial-gate-results.json`: stale/open finding/excluded citation negative cases.
- `handoff/vlearn-rebuild-step3-5-20261009/checker/real-source-recovery-and-review.json`: real chart recovery, rejected question/hint và rubric trials.
- `handoff/vlearn-rebuild-step3-5-20261009/controller/pilot-evidence-report.json`: controller rerun zero blockers; trạng thái vẫn `work_records_complete_needs_semantic_review`.
- `handoff/vlearn-rebuild-step3-5-20261009/controller/changed-context-blocked.json`: không tái dùng review cho context khác.
- `handoff/vlearn-rebuild-step3-5-20261009/controller/tests.log`: regression 52 tests.

### Chưa được nghiệm thu

1. Một Day Phase 2 hoàn chỉnh từ toàn bộ nguồn chính/tham khảo, coverage đủ Day, ZIP và preview môi trường đích (bước 6).
2. Mapping production, import/publish hoặc bốn trải nghiệm student trên deployment.
3. Runtime AI rubric/provider, difficulty calibration, hiệu quả với học viên thật và khả năng tổng quát sang mọi nguồn.
4. Skill không tự sửa dữ kiện mất khỏi nguồn; công cụ hỗ trợ phục hồi và chặn phần chưa xác minh, agent vẫn phải đối chiếu pixels/nguồn và xin đúng dữ kiện nếu cần.

**Cách báo cáo đúng:** bước 3–5 đã có công cụ vận hành, negative gates và trial thực tế được kiểm độc lập trong phạm vi nhỏ. Bước 6 còn làm; không nói toàn bộ rebuild hoặc bộ Phase 2 đã xong.
