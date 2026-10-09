# Thiết kế rebuild — 2026-10-09

## Đầu vào và các chế độ làm việc

Agent nhận PDF/tài liệu, context giảng viên và yêu cầu bằng ngôn ngữ tự nhiên. Có thể biên soạn kho mới, tạo bộ câu theo đoạn đang học, hoặc sửa bộ đã có. Agent diễn giải request thành context có cấu trúc và ghi giả định; script không thay NLP bằng heuristic keyword.

Hai loại context tách riêng:

- **Evidence context:** lời giảng/ghi chú hỗ trợ kiến thức; cần nguồn và attribution.
- **Teaching context:** đang ở unit/trang nào, đã học gì, chưa học gì, mục đích kiểm tra; điều khiển phạm vi và thiết kế câu, không tự trở thành bằng chứng chuyên môn.

## Mô hình nội dung

`Source → Extraction → Learning unit → KC → Assessment slot → Question variants → Contextual question set → VLearn ZIP`

Learning unit là đoạn học nhỏ có mục tiêu và ranh giới; có thể gồm nhiều KC, hoặc một KC được dạy từng phần ở nhiều unit. Group tổ chức kiến thức; module trong blueprint là cấu trúc delivery. Không ép unit = group = module. Sidecar lưu mapping explicit; không thêm root field vào hai JSON VLearn.

Bank và context selection tách riêng: kho đầy đủ một Day được xuất VLearn; chọn bộ theo context sinh plan ngoài ZIP, không sửa/truncate bank rồi làm gãy slot/variant. Khi cần bộ riêng, agent phải chủ động dựng lại graph nhất quán và kiểm lại, giữ bản gốc. VLearn tự chạy quiz theo vị trí slide là tính năng ứng dụng riêng, chưa được implementation skill này cung cấp.

## Thành phần

| Thành phần | Thực thi | Bằng chứng cần có |
|---|---|---|
| Phục hồi nguồn | Agent chọn render/crop/OCR/source alternative phù hợp, kiểm lại và lưu record | Vùng nguồn, attempt, artifact, kết quả kiểm, phần còn thiếu, KC/câu bị ảnh hưởng |
| Unit/KC design | Agent viết mục tiêu, phạm vi, prerequisite, source windows; thử phản hồi học viên đối lập | Lý do tách/gộp và coverage, không chỉ nhãn atomic |
| Quiz theo context | Agent chọn/sinh câu; `context_plan.py` kiểm graph và tính candidate pool theo khai báo | Unit/target/available/excluded IDs, annotation yêu cầu kiến thức, gap đang mở, report loại câu và lý do |
| Review học thuật | Agent giải câu, kiểm strong alternative/hint/rubric/VI–EN | Findings cụ thể, sửa gì, phần chưa duyệt; self-review khác independent approval |
| Xuất VLearn | `package_day.py` hiện có | ZIP hai file, contract report, target evidence; preview thật kiểm riêng |

## Contract ngoài ZIP

`authoring-context.v1`: request + units + question annotations + open source gaps. Chi tiết và ví dụ ở `references/context.md` trong skill. `source-recovery.v1` và academic review record được mô tả trong các references tương ứng; chưa có parser tự chứng nhận chúng đúng về nghĩa.

`context_plan.py` chỉ kiểm khai báo. Không tự chấm mức khó, đo độ hay của câu, phán lời giải đúng hay biết OCR đọc đúng. Unknown/missing annotation không được coi là eligible; gap nguồn mở loại phần bị ảnh hưởng. Report luôn cần agent review. Nếu không đủ câu, trả shortage, không lặp câu hay nới phạm vi để đủ số.

## Thử nghiệm và nghiệm thu

- Technical: regression packager; contextual candidate cases có kiến thức chưa học, gap nguồn, thiếu annotation, integrated question và nhiều unit.
- Behavioral: agent làm recovery và quiz theo các context đối lập trên nguồn được cung cấp, lưu quyết định và artefact thực tế. Không dùng test regex headings làm chứng minh chất lượng.
- Pilot: một Day Phase 2 nguồn đã đối chiếu → đọc đầy đủ → units/KC → Quiz VI/EN → review → ZIP → preview VLearn. Sau đó đối chiếu các yêu cầu/context ít nhất: giữa bài, cuối bài và đoạn chưa học để phát hiện hỏi vượt phạm vi. Phạm vi/quota do nguồn và yêu cầu quyết định.

Đã triển khai source workbench và review evidence checker, cùng context checker hiện có. Trial thật gồm reference Interviews ba trang, hai unit/KC, ba câu VI/EN và context đối lập; checker độc lập phát hiện/sửa lệch rubric, controller đối chiếu evidence. Một slice First Principles kiểm phục hồi quan hệ biểu đồ và qualifier. Chi tiết ở [acceptance-audit.md](acceptance-audit.md).

**Pilot toàn Day thật, review toàn Day và preview VLearn chưa hoàn thành**. Trial học phần nhỏ không chứng minh chất lượng trên mọi nguồn hoặc runtime chấm rubric. Chưa thay skill cũ hoàn toàn hoặc tuyên bố bộ Phase 2 đã sẵn sàng.
