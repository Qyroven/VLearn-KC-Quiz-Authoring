# Biên soạn từ nguồn

## Extraction

- Lập inventory PDF: đường dẫn, SHA-256, số trang, material ID nếu có, vai trò chính/tham khảo và course/Day nguồn đã đối chiếu. Cùng một PDF có thể xuất hiện ở nhiều activity; không nhân đôi nội dung chỉ vì tên activity khác.
- Đọc text cùng hình render. Giữ bảng, công thức, code, trục/nhãn sơ đồ và mối quan hệ cần hiểu. OCR hoặc text extraction riêng không đủ để kết luận đã đọc hình.
- Mỗi trang có block theo thứ tự đọc, vị trí nguồn, nội dung trích xuất và `page_note` do agent viết để diễn đạt kiến thức/quan hệ; tách uncertainty. Trang ít nội dung vẫn ghi đã kiểm, không bịa thêm.
- Ngữ cảnh giảng viên có nguồn riêng, không ghép thành lời có sẵn trên slide. Nếu hình mờ/mất trang/nguồn mâu thuẫn thì ghi phạm vi bị ảnh hưởng; hỏi khi thiếu dữ kiện quyết định khả năng trả lời.
- Giữ raw PDF và Extraction ngoài ZIP. Đường dẫn `extraction_path` phải ổn định và truy được từ bộ bàn giao.

## KC và blueprint

Một leaf KC mô tả năng lực quan sát được, đủ nhỏ để chẩn đoán và đủ ngữ cảnh để đứng độc lập. Group chỉ tổ chức các KC liên quan. Ví dụ “RAG” quá rộng; “chọn retrieval strategy theo loại câu hỏi và bằng chứng cho trước” có thể đo được nếu nguồn dạy điều đó. Không biến từng bullet thành một KC hoặc bịa prerequisite.

Giữ `knowledge` giải thích đầy đủ, `observable_claim`, nguồn trang, ngữ cảnh và các giới hạn. Chọn `is_core`/placement theo quyết định chương trình, không tự đánh dấu tất cả core. Blueprint gắn module và slot với năng lực; câu initial/reassessment đo cùng mục tiêu nhưng không chỉ đổi số rồi coi là phủ kiến thức mới. Hoạt động phối hợp nhiều KC ghi contributing/component IDs thay vì giả vờ là một leaf.

## Quiz và tự kiểm

- Giải mỗi câu trước khi chốt đáp án; kiểm strong alternative có thể đúng, tính đầy đủ của dữ kiện, đơn vị/tolerance và ambiguity.
- Hints hướng tới bước suy nghĩ tiếp theo. Với câu cần chọn strategy, hint không được nêu luôn strategy đúng; với câu tính toán, hint không thay học viên thực hiện phép tính cần đo.
- Lời giải giải thích vì sao đúng và điểm dễ nhầm, không chỉ lặp answer key. Câu hỏi đủ dữ kiện ngay khi xuất hiện; hint không chứa dữ kiện bắt buộc bị thiếu khỏi đề.
- Rubric tách tiêu chí có thể quan sát, điểm và exemplar; chấp nhận cách diễn đạt tương đương khi phù hợp. Mức khó độc lập với cognitive operation. Không ép câu học thuộc thành Apply chỉ để tăng nhãn.
- Dịch cả stem/choices/hints/explanation/rubric. Giữ đúng nghĩa, độ khó, đơn vị, đáp án và mức tiết lộ gợi ý; không yêu cầu prose VI/EN giống số bullet.
- Tự kiểm nội dung không phải independent review. Báo rõ ai đã duyệt, phạm vi và những vấn đề còn mở. Không tự tạo dấu approved.

Không có quota câu/trang/KC. Báo phần đã phủ, phần chưa phủ và lý do. Dữ liệu hợp schema nhưng sơ sài vẫn chưa đạt học thuật.
