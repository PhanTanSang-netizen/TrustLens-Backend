# Backend Activity Log Update - TrustLens

## Cập nhật ngày 15/06/2026

### 1. Tổng quan tiến độ hôm nay

Trong ngày 15/06/2026, backend TrustLens đã được cập nhật từ mức **backend skeleton** sang mức **backend foundation có API upload chạy được ở bản dev/local**.

Các nhóm công việc chính đã hoàn thành:

* Bổ sung Upload API cho submission.
* Bổ sung Job Status API dạng mock.
* Cấu hình CORS để backend có thể kết nối với frontend local.
* Chuẩn hóa lại module backend theo SRS.
* Bổ sung các thư mục và file skeleton cho export, models, schemas và services.
* Commit các thay đổi thành 2 nhóm rõ ràng.

---

## 2. Các thay đổi đã thực hiện

### 2.1. Thêm Upload API bản dev/local

Đã triển khai endpoint:

```txt
POST /api/v1/submissions/upload
```

API này hỗ trợ:

* Nhận file upload dạng `multipart/form-data`.
* Hỗ trợ file `.pdf` và `.docx`.
* Kiểm tra extension file.
* Kiểm tra MIME type.
* Kiểm tra file rỗng.
* Kiểm tra giới hạn dung lượng file.
* Lưu file vào thư mục local `uploads/`.
* Tạo `file_id`.
* Tạo `submission_id`.
* Tạo `job_id`.
* Tạo checksum SHA-256 cho file.
* Trả về response JSON cho frontend.

Kết quả test thực tế đã upload thành công file:

```txt
Lab 1.docx
```

Thông tin trả về gồm:

```txt
submission_id
assignment_id
owner_label
file_id
original_name
stored_name
stored_path
mime_type
size_bytes
checksum
job_id
status
progress
step
error_code
```

Trạng thái trả về:

```txt
submission.status = UPLOADED
job.status = QUEUED
job.progress = 0
job.step = queued
```

Ghi chú: Upload API hiện tại mới là bản dev/local, chưa lưu dữ liệu vào PostgreSQL.

---

### 2.2. Thêm Job Status API mock

Đã triển khai endpoint:

```txt
GET /api/v1/jobs/{job_id}
```

Mục đích:

* Cho phép frontend kiểm tra trạng thái xử lý của file.
* Chuẩn bị cho job status panel ở frontend.
* Chuẩn bị cho worker pipeline sau này.

Response hiện tại là mock:

```json
{
  "job_id": "...",
  "status": "QUEUED",
  "progress": 0,
  "step": "queued",
  "error_code": null
}
```

Ghi chú: Job status hiện chưa đọc từ database thật.

---

### 2.3. Cập nhật API router

Đã cập nhật `app/api/v1/api_router.py` để include các router chính:

```txt
Health
Submissions
Jobs
```

Các endpoint hiện có:

```txt
GET  /api/v1/health
POST /api/v1/submissions/upload
GET  /api/v1/jobs/{job_id}
```

---

### 2.4. Cập nhật Health API

Đã chỉnh lại endpoint health check để endpoint cuối cùng là:

```txt
GET /api/v1/health
```

Response:

```json
{
  "status": "ok",
  "service": "TrustLens Backend"
}
```

---

### 2.5. Cập nhật CORS trong FastAPI

Đã cập nhật `app/main.py` để cho phép frontend local gọi backend.

Các origin được cho phép:

```txt
http://localhost:5173
http://127.0.0.1:5173
http://localhost:3000
http://127.0.0.1:3000
```

Mục đích:

* Cho phép React frontend chạy song song với FastAPI backend.
* Tránh lỗi CORS khi frontend gọi API upload.
* Chuẩn bị cho tích hợp frontend/backend.

---

### 2.6. Cập nhật dependencies

Đã cập nhật `requirements.txt`.

Package quan trọng đã bổ sung:

```txt
python-multipart
```

Mục đích:

* FastAPI cần package này để xử lý `multipart/form-data`.
* Đây là package bắt buộc cho chức năng upload file.

---

## 3. Chuẩn hóa cấu trúc module theo SRS

### 3.1. Bổ sung export module

Đã thêm thư mục:

```txt
app/export/
```

Gồm các file:

```txt
app/export/__init__.py
app/export/pdf_exporter.py
app/export/docx_exporter.py
app/export/xlsx_exporter.py
```

Mục đích:

* Chuẩn bị cho chức năng export report.
* Hỗ trợ export theo các định dạng PDF, DOCX, XLSX trong giai đoạn sau.
* Tách logic export khỏi `services/` và `reports.py`.

---

### 3.2. Bổ sung models theo SRS

Đã bổ sung các model skeleton còn thiếu theo logical data model của SRS:

```txt
app/models/role_permission.py
app/models/term.py
app/models/student.py
app/models/extracted_document.py
app/models/reference_section.py
app/models/citation_field.py
app/models/score_component.py
app/models/trust_score.py
app/models/scoring_config.py
app/models/metadata_provider.py
```

Các model này chuẩn bị cho các nhóm dữ liệu:

* Phân quyền người dùng.
* Học kỳ.
* Sinh viên.
* Tài liệu đã trích xuất.
* Section tài liệu tham khảo.
* Trường dữ liệu citation.
* Điểm thành phần.
* Trust Score tổng.
* Cấu hình chấm điểm.
* Nhà cung cấp metadata.

---

### 3.3. Xóa model cũ không còn phù hợp

Đã xóa:

```txt
app/models/score.py
```

Lý do:

* Theo hướng SRS, score nên được tách rõ thành:

  * `score_component.py`
  * `trust_score.py`
* Tránh gom tất cả logic điểm vào một file chung `score.py`.
* Giúp database schema rõ ràng hơn khi tạo migration.

Ghi chú kỹ thuật: Git hiển thị dòng rename từ `score.py` sang `db/__init__.py` vì hai file đều rỗng. Điều này không ảnh hưởng đến code.

---

### 3.4. Bổ sung schemas theo SRS

Đã bổ sung các schema skeleton:

```txt
app/schemas/admin_schema.py
app/schemas/audit_log_schema.py
app/schemas/citation_schema.py
app/schemas/class_schema.py
app/schemas/extracted_document_schema.py
app/schemas/file_schema.py
app/schemas/metadata_provider_schema.py
app/schemas/metadata_schema.py
app/schemas/reference_section_schema.py
app/schemas/role_permission_schema.py
app/schemas/score_schema.py
app/schemas/scoring_config_schema.py
app/schemas/student_schema.py
app/schemas/term_schema.py
```

Mục đích:

* Chuẩn bị request/response schema cho các module sau.
* Giữ quy ước đặt tên theo hậu tố `_schema.py`.
* Tách Pydantic schema khỏi SQLAlchemy model.

---

### 3.5. Bổ sung services theo SRS

Đã bổ sung các service skeleton:

```txt
app/services/admin_service.py
app/services/class_service.py
app/services/export_service.py
app/services/user_service.py
```

Mục đích:

* Tách business logic khỏi endpoint.
* Chuẩn bị logic cho quản trị, lớp học phần, export và user.
* Giữ kiến trúc backend theo hướng endpoint → service → model/database.

---

### 3.6. Bổ sung database package initializer

Đã thêm:

```txt
app/db/__init__.py
```

Mục đích:

* Đảm bảo `app/db` là Python package.
* Hỗ trợ import ổn định cho database layer.
* Chuẩn bị cho Alembic và SQLAlchemy models.

---

## 4. Commit đã tạo hôm nay

### Commit 1

```txt
80081d3 feat: add local upload and job status API
```

Nội dung:

* Cập nhật API router.
* Thêm/sửa Health API.
* Thêm Upload API.
* Thêm Job Status API mock.
* Cập nhật CORS trong `main.py`.
* Cập nhật `requirements.txt`.

---

### Commit 2

```txt
d1b61b0 chore: align backend modules with SRS
```

Nội dung:

* Bổ sung `app/export/`.
* Bổ sung các model skeleton theo SRS.
* Bổ sung các schema skeleton theo SRS.
* Bổ sung các service skeleton theo SRS.
* Thêm `app/db/__init__.py`.
* Xóa `app/models/score.py`.

---

## 5. Kết quả đạt được trong ngày

| Hạng mục                               | Trạng thái |
| -------------------------------------- | ---------- |
| Upload API local/dev                   | Hoàn thành |
| Upload DOCX test thực tế               | Hoàn thành |
| Sinh checksum SHA-256                  | Hoàn thành |
| Sinh `submission_id`                   | Hoàn thành |
| Sinh `file_id`                         | Hoàn thành |
| Sinh `job_id`                          | Hoàn thành |
| Job Status API mock                    | Hoàn thành |
| CORS cho frontend local                | Hoàn thành |
| API router cho Health/Submissions/Jobs | Hoàn thành |
| Export module skeleton                 | Hoàn thành |
| Models skeleton theo SRS               | Hoàn thành |
| Schemas skeleton theo SRS              | Hoàn thành |
| Services skeleton theo SRS             | Hoàn thành |
| Xóa model score cũ                     | Hoàn thành |
| Commit upload API                      | Hoàn thành |
| Commit chuẩn hóa module SRS            | Hoàn thành |

---

## 6. Trạng thái backend hiện tại

Backend hiện tại đã đạt trạng thái:

```txt
Backend MVP Foundation + Upload Flow Dev Completed
```

Backend đã có:

* Cấu trúc module bám theo SRS.
* API upload file chạy được.
* API job status mock.
* CORS cho frontend.
* Các module skeleton cho database, processing, scoring, metadata, report và export.

Tuy nhiên, backend vẫn chưa có persistence thật cho upload flow.

---

## 7. Các phần chưa hoàn thành

Các phần còn thiếu:

* Chưa push commit mới lên GitHub nếu chưa chạy `git push`.
* Chưa tạo PostgreSQL schema thật.
* Chưa tạo Alembic migration cho các bảng upload flow.
* Chưa lưu `files`, `submissions`, `processing_jobs` vào database.
* Chưa có job status đọc từ database.
* Chưa có worker xử lý file thật.
* Chưa trích xuất nội dung PDF/DOCX thật.
* Chưa nhận diện section tài liệu tham khảo thật.
* Chưa tách citation thật.
* Chưa metadata lookup thật.
* Chưa tính Trust Score thật.
* Chưa sinh report thật.
* Chưa export PDF/DOCX/XLSX thật.

---

## 8. Công việc tiếp theo

Bước tiếp theo nên thực hiện là:

```txt
Database Phase 1 - Upload Flow Tables
```

Các bảng cần làm trước:

```txt
users
courses
classes
assignments
files
submissions
processing_jobs
```

Thứ tự đề xuất:

1. Kiểm tra lại `git status`.
2. Push 2 commit mới lên GitHub nếu chưa push.
3. Viết SQLAlchemy model thật cho 7 bảng upload flow.
4. Kiểm tra `app/models/__init__.py` chỉ import các model cần migration ở phase này.
5. Cấu hình Alembic nhận `Base.metadata`.
6. Tạo migration đầu tiên:

```txt
alembic revision --autogenerate -m "create upload flow tables"
```

7. Apply migration:

```txt
alembic upgrade head
```

8. Kiểm tra PostgreSQL đã có bảng.
9. Sửa Upload API để lưu dữ liệu thật vào PostgreSQL.
10. Sửa Job API để đọc job status thật từ database.

---

## 9. Ghi chú kỹ thuật

* Upload API hiện tại vẫn là dev/local version.
* Không commit thư mục `uploads/`.
* Không commit `.env`.
* Không commit `.venv`.
* Các file mới trong `models/`, `schemas/`, `services/`, `export/` hiện chủ yếu là skeleton.
* Không nên import toàn bộ model skeleton vào Alembic ngay.
* Phase database đầu tiên chỉ nên tập trung vào 7 bảng phục vụ upload flow.
