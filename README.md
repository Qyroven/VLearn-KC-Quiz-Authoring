# VLearn KC & Quiz Authoring

Skill mới dành cho biên soạn học liệu import VLearn. Đầu ra một Day là ZIP gồm **`kc.json` + `quiz.json`**, mỗi file có VI/EN; Extraction, PDF và báo cáo ở ngoài ZIP. Không thay thế hoặc ghi đè skill `learning-authoring-pipeline` cũ.

Rebuild gồm phục hồi nguồn, learning units nhỏ, quiz theo context đang học và review học thuật. Xem [audit bản cũ](docs/legacy-audit.md) và [thiết kế rebuild](docs/rebuild-design.md). Đã có instructions, context checker, workbench PDF recovery và checker records nguồn/coverage/review gắn revision. Xem [workflow bước 3–5](skills/vlearn-kc-quiz-authoring/references/evidence-workflow.md).

[Pilot bước 6 — Day16 Track1](docs/step6-acceptance.md): đã đọc/review độc lập toàn bộ 66 trang của hai PDF, biên soạn 25 KC, 24 learning unit và 28 câu VI/EN; local contract, evidence và sáu context case đều qua kiểm. Preview ZIP cuối trên **vlearn.dev** bị chặn vì khóa K04-L34-P2-T1 chưa được admin gắn cohort/track nguồn. **Chưa nghiệm thu import production hoặc toàn Day**; năm video và lab nằm ngoài phạm vi đã đọc, `source_day` vẫn chưa xác minh. Không import nháp/publish.

[Nghiệm thu bước 3–5](docs/acceptance-audit.md): 52 regression tests pass; có trial nguồn thật ba trang, hai unit/KC và ba câu VI/EN với review độc lập, cùng ca phục hồi biểu đồ. Đây là nghiệm thu phạm vi nhỏ, không phải toàn bộ Day hay production.

## Dùng

Đọc [SKILL.md](skills/vlearn-kc-quiz-authoring/SKILL.md), [contract](skills/vlearn-kc-quiz-authoring/references/contract.md), rồi soạn trực tiếp payload native. Python 3.10+; packager dùng standard library, không cần API key.

```sh
python3 skills/vlearn-kc-quiz-authoring/scripts/package_day.py \
  --kc /path/to/day/kc.json --quiz /path/to/day/quiz.json \
  --out /path/to/new-delivery-directory
python3 -m unittest discover -s tests -v
```

Tạo plan câu theo đoạn học (không thay bank):

```sh
python3 skills/vlearn-kc-quiz-authoring/scripts/context_plan.py \
  --kc /path/to/day/kc.json --quiz /path/to/day/quiz.json \
  --context /path/to/day/authoring-context.json
```

Agent nhận context tự nhiên rồi chuẩn hóa theo [context contract](skills/vlearn-kc-quiz-authoring/references/context.md); không bắt giảng viên nhập JSON. Script chỉ kiểm phạm vi đã khai báo, trả candidate IDs và shortage; agent chọn/sinh câu và kiểm chất lượng riêng.

Không có `--out` thì chỉ kiểm. Có thể thêm `--target /path/to/target-evidence.json` để kiểm mapping theo evidence đã đọc. Thư mục output mới chứa `package.zip` và `validation-report.json`; script không ghi đè output có sẵn.

## Cài skill

Copy riêng thư mục `skills/vlearn-kc-quiz-authoring` vào thư mục skills của Codex (ví dụ `~/.codex/skills/`), giữ cả scripts/vendor và references. Không chép đè skill cũ. Mở phiên mới để skill được discovery. Gọi `$vlearn-kc-quiz-authoring` và cung cấp nguồn cùng course/Day đích.

## Phạm vi đã kiểm

Vendor gồm pair adapter và content graph từ backend chính thức, nguyên byte và có checksum/provenance. Loader chỉ đổi import trong bộ nhớ. Guard bổ sung kiểm prompt, version/points, membership và VI/EN score policy. ZIP deterministic và giữ nguyên bytes của hai JSON.

**Local pass không chứng minh preview/publish trên production hoặc chất lượng học thuật.** Mapping chưa cung cấp sẽ báo `unverified`. AI rubric cần xác minh provider/flag/runtime trên môi trường đích; packager không gọi grader. Ví dụ trong references là synthetic technical fixture, không dùng làm học liệu Phase 2.

Nền tảng biên soạn kế thừa định hướng nguồn → Extraction → KC → Quiz của [KC-Quiz-Mastery](https://github.com/Qyroven/KC-Quiz-Mastery); skill mới không mang portal/Supabase/offline scorer sang. Hợp đồng xuất file theo [vlearn-rebuild](https://github.com/vinuni-vlearn/vlearn-rebuild), revision trong [provenance](skills/vlearn-kc-quiz-authoring/scripts/vendor/provenance.json).
