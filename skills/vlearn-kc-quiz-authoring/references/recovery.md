# Phục hồi nguồn và quản lý ảnh hưởng

Có helper thực thi render/crop/OCR và provenance tại [evidence-workflow.md](evidence-workflow.md). Khi dùng evidence checker, đưa records bên dưới vào `review.json.source_recovery`; các issue mở phải đồng bộ với context.

## Xử lý theo lỗi thật

| Lỗi | Hành động phù hợp | Kiểm lại |
|---|---|---|
| Text layer sai/mất ký tự | Đối chiếu ảnh render; thử extractor khác hoặc OCR đúng ngôn ngữ | So chữ, số, dấu, đơn vị với trang; OCR không tự thành ground truth |
| Bảng/hình/sơ đồ quá nhỏ | Render trang rõ hơn và crop vùng cần đọc; giữ trang đầy đủ để biết quan hệ/ngữ cảnh | Kiểm header↔cell, nhãn/legend/trục, chiều arrow và điều kiện ngoài crop |
| Trang/file thiếu hoặc hỏng | Tìm bản nguồn khác trong tài liệu/quyền truy cập đã được giao | Đối chiếu version, số trang và vị trí; lưu provenance, không thay file âm thầm |
| Hai nguồn mâu thuẫn | Giữ nguyên hai phát biểu và ngữ cảnh; xem có khác điều kiện/phiên bản hay không | Không chọn phát biểu quen thuộc hơn làm đúng; xin xác nhận khi ảnh hưởng đáp án |

Không bắt buộc thử tất cả tool cho mọi lỗi. Chọn cách có khả năng giải quyết dữ kiện cụ thể. Nếu thử mới không cung cấp bằng chứng mới, cần bản nguồn rõ hơn hoặc xác nhận của giảng viên; không lặp OCR vô hạn hoặc đoán từ kiến thức nền.

## Recovery record ngoài ZIP

Ví dụ minh họa `source-recovery.v1`, không phải dữ liệu đã được phục hồi:

```json
{
  "schema_version":"source-recovery.v1",
  "issues":[{
    "issue_id":"gap-figure-label",
    "source_id":"slides-primary",
    "page":14,
    "region_description":"legend phía phải biểu đồ",
    "missing_fact":"đơn vị trục Y",
    "attempts":[{"method":"render_and_crop","artifact":"review/page14-legend.png","result":"ký tự vẫn không phân biệt được"}],
    "status":"needs_source",
    "affected_kc_ids":["kc-chart-reading"],
    "affected_question_ids":["q-chart-threshold"],
    "next_action":"Xin trang 14 bản gốc hoặc giảng viên xác nhận đơn vị trục Y"
  }]
}
```

Status phù hợp: `recovered_verified`, `partially_recovered`, `needs_source`, `needs_lecturer_confirmation`. Với status recovered, record phải có dữ kiện phục hồi, cách đối chiếu và provenance, không chỉ “OCR pass”. Partial giữ phần đã xác minh và phần chưa rõ riêng.

## Tiếp tục và sửa downstream

- Phần độc lập đủ nguồn tiếp tục soạn. Câu phụ thuộc dữ kiện mở chưa được đưa vào bộ dùng được. Thêm issue ID vào `open_source_gaps` của context, chỉ rõ KC/câu ảnh hưởng.
- Khi thiếu dữ kiện cần thiết, yêu cầu cụ thể: trang nào, vùng nào, dữ kiện gì; không yêu cầu người dùng nhập lại cả bài.
- Chỉ đóng gap sau khi kiểm bằng chứng mới. Sau sửa nguồn, đọc lại Extraction và kiểm KC/slot/question/hints/rubric bị ảnh hưởng. Không tái sử dụng status review cũ cho nội dung đã đổi.
- Hình bắt buộc để trả lời phải có trong đề hoặc biểu diễn tương đương đủ dữ kiện; một citation hay hint không thay được hình thiếu.
