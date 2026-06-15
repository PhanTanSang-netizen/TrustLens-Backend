# Backend Activity Log - TrustLens

## 1. Thông tin chung

| Mục             | Nội dung                                  |
| --------------- | ----------------------------------------- |
| Dự án           | TrustLens                                 |
| Module          | Backend                                   |
| Người thực hiện | Phan Tấn Sang                             |
| Vai trò         | Backend - Server, Database, API Structure |
| Ngày cập nhật   | 15/06/2026                                |
| Repository      | TrustLens-Backend                         |
| Branch          | main                                      |
| Commit gần nhất | 701f881                                   |

---

## 2. Mục tiêu công việc

Mục tiêu của giai đoạn này là chuẩn hóa lại cấu trúc backend theo hướng module hóa, phục vụ cho việc phát triển các chức năng chính của TrustLens trong các bước tiếp theo.

Backend được tổ chức để hỗ trợ các nhóm chức năng chính:

* RESTful API.
* Cấu hình hệ thống.
* Kết nối database.
* Quản lý models.
* Quản lý schemas request/response.
* Service layer.
* File processing.
* Citation processing.
* Metadata lookup.
* NLP/relevance scoring.
* Trust Score processing.
* Background worker.
* Utility functions.

---

## 3. Các hoạt động đã thực hiện

### 3.1. Chuẩn hóa cấu trúc thư mục backend

Đã tái cấu trúc thư mục `apps/backend/app` theo hướng rõ ràng hơn:

```txt
app/
├── api/
├── core/
├── db/
├── models/
├── schemas/
├── services/
├── processing/
├── utils/
└── workers/
```

Ý nghĩa từng thư mục:

| Thư mục       | Vai trò                                                   |
| ------------- | --------------------------------------------------------- |
| `api/`        | Chứa các API endpoint của hệ thống                        |
| `core/`       | Chứa cấu hình, bảo mật, phân quyền, exception, logging    |
| `db/`         | Chứa cấu hình kết nối database và SQLAlchemy base         |
| `models/`     | Chứa SQLAlchemy models tương ứng với database tables      |
| `schemas/`    | Chứa Pydantic schemas cho request/response                |
| `services/`   | Chứa business logic của hệ thống                          |
| `processing/` | Chứa logic xử lý file, citation, metadata, NLP và scoring |
| `utils/`      | Chứa các hàm tiện ích dùng chung                          |
| `workers/`    | Chứa cấu hình worker xử lý nền                            |

---

### 3.2. Chuẩn hóa API layer

Đã tạo cấu trúc API versioning:

```txt
app/api/v1/
├── api_router.py
└── endpoints/
    ├── admin.py
    ├── assignments.py
    ├── auth.py
    ├── classes.py
    ├── courses.py
    ├── health.py
    ├── jobs.py
    ├── reports.py
    ├── submissions.py
    └── users.py
```

Mục đích:

* Tách API theo từng nhóm chức năng.
* Dễ mở rộng khi thêm endpoint mới.
* Chuẩn bị cho các API chính như upload file, job status, report, auth và academic management.

---

### 3.3. Thêm health check endpoint

Đã tạo endpoint kiểm tra trạng thái backend:

```txt
GET /api/v1/health
```

Mục đích:

* Kiểm tra backend có chạy hay không.
* Dùng cho giai đoạn demo, test local và kiểm tra triển khai.

Kết quả mong đợi:

```json
{
  "status": "ok",
  "service": "TrustLens Backend"
}
```

---

### 3.4. Chuẩn hóa core configuration

Đã cập nhật thư mục `app/core` gồm:

```txt
core/
├── config.py
├── security.py
├── permissions.py
├── exceptions.py
└── logging.py
```

Trong đó:

| File             | Vai trò                             |
| ---------------- | ----------------------------------- |
| `config.py`      | Đọc cấu hình từ `.env`              |
| `security.py`    | Chuẩn bị cho JWT/password hashing   |
| `permissions.py` | Chuẩn bị cho phân quyền theo role   |
| `exceptions.py`  | Chuẩn bị xử lý exception thống nhất |
| `logging.py`     | Chuẩn bị logging hệ thống           |

---

### 3.5. Thêm database layer

Đã tạo thư mục:

```txt
app/db/
├── base.py
├── session.py
└── init_db.py
```

Mục đích:

* Chuẩn bị kết nối PostgreSQL.
* Chuẩn bị SQLAlchemy Base.
* Chuẩn bị cho Alembic migration.
* Tách database layer khỏi `core`.

File cũ `app/core/database.py` đã được xóa vì không còn phù hợp với cấu trúc mới.

---

### 3.6. Chuẩn hóa models

Đã chuẩn hóa thư mục `app/models` theo cấu trúc mới:

```txt
models/
├── user.py
├── course.py
├── class_model.py
├── assignment.py
├── submission.py
├── file.py
├── processing_job.py
├── citation.py
├── metadata_record.py
├── score.py
├── warning.py
├── report.py
├── audit_log.py
└── __init__.py
```

Các file model cũ đã được xóa:

```txt
analysis_job.py
document.py
export.py
metadata_check.py
reference.py
```

Lý do xóa:

* Tên file chưa thống nhất với cấu trúc mới.
* Một số file bị trùng vai trò với model chuẩn mới.
* Cần chuẩn hóa tên model trước khi tạo database schema bằng Alembic.

---

### 3.7. Chuẩn hóa schemas

Đã chuẩn hóa thư mục `app/schemas`:

```txt
schemas/
├── auth_schema.py
├── user_schema.py
├── course_schema.py
├── assignment_schema.py
├── submission_schema.py
├── job_schema.py
├── report_schema.py
├── common_schema.py
└── __init__.py
```

Mục đích:

* Tách schemas khỏi models.
* Chuẩn bị cho request/response validation của FastAPI.
* Giữ quy ước đặt tên rõ ràng bằng hậu tố `_schema.py`.

---

### 3.8. Chuẩn hóa services

Đã chuẩn hóa thư mục `app/services`:

```txt
services/
├── auth_service.py
├── course_service.py
├── assignment_service.py
├── submission_service.py
├── file_storage_service.py
├── job_service.py
├── report_service.py
├── audit_service.py
└── __init__.py
```

Mục đích:

* Tách business logic khỏi endpoint.
* Chuẩn bị cho các chức năng như upload file, tạo submission, tạo processing job và sinh report.

---

### 3.9. Thêm processing layer

Đã tạo cấu trúc xử lý nghiệp vụ chuyên sâu:

```txt
processing/
├── extraction/
│   ├── pdf_extractor.py
│   ├── docx_extractor.py
│   └── reference_detector.py
│
├── citation/
│   ├── citation_splitter.py
│   ├── citation_parser.py
│   ├── citation_normalizer.py
│   └── style_detector.py
│
├── metadata/
│   ├── crossref_client.py
│   ├── openalex_client.py
│   ├── semantic_scholar_client.py
│   └── metadata_matcher.py
│
├── nlp/
│   ├── topic_extractor.py
│   ├── embedding_service.py
│   └── relevance_scorer.py
│
└── scoring/
    ├── format_score.py
    ├── existence_score.py
    ├── credibility_score.py
    ├── recency_score.py
    ├── relevance_score.py
    ├── trust_score.py
    └── warning_generator.py
```

Mục đích:

* Tách rõ các bước xử lý file.
* Chuẩn bị pipeline: extract text → detect references → parse citation → lookup metadata → relevance scoring → trust score → warning generation.
* Tránh để nhiều file xử lý nằm trực tiếp trong `processing/`.

---

### 3.10. Thêm worker layer

Đã tạo:

```txt
workers/
├── celery_app.py
└── tasks.py
```

Mục đích:

* Chuẩn bị cho xử lý bất đồng bộ.
* Sau này dùng cho file processing, metadata lookup và scoring.
* Tránh để request upload bị block quá lâu.

---

### 3.11. Cập nhật môi trường cấu hình

Đã thêm:

```txt
.env.example
```

Mục đích:

* Cung cấp file mẫu cho biến môi trường.
* Không đưa `.env` thật lên GitHub.
* Giúp thành viên khác biết cần cấu hình gì khi chạy backend local.

Đã cập nhật `.gitignore` để loại trừ:

```txt
.env
.venv/
__pycache__/
*.pyc
uploads/
exports/
_backup_cleanup/
```

---

### 3.12. Cập nhật dependencies

Đã cài và cập nhật các package nền tảng:

```txt
fastapi
uvicorn
sqlalchemy
alembic
psycopg2-binary
pydantic-settings
python-dotenv
```

Mục đích:

* Chạy FastAPI backend.
* Kết nối PostgreSQL.
* Chuẩn bị migration bằng Alembic.
* Đọc cấu hình môi trường từ `.env`.

---

### 3.13. Commit và push thay đổi

Đã commit và push cấu trúc backend mới lên GitHub.

Commit gần nhất:

```txt
701f881
```

Repository đã được cập nhật lên branch:

```txt
main
```

---

## 4. Kết quả đạt được

| Hạng mục                           | Trạng thái |
| ---------------------------------- | ---------- |
| Chuẩn hóa backend folder structure | Hoàn thành |
| Tách API layer                     | Hoàn thành |
| Tách core configuration            | Hoàn thành |
| Thêm database layer                | Hoàn thành |
| Chuẩn hóa models                   | Hoàn thành |
| Chuẩn hóa schemas                  | Hoàn thành |
| Chuẩn hóa services                 | Hoàn thành |
| Thêm processing layer              | Hoàn thành |
| Thêm workers layer                 | Hoàn thành |
| Cập nhật `.env.example`            | Hoàn thành |
| Cập nhật `.gitignore`              | Hoàn thành |
| Commit và push lên GitHub          | Hoàn thành |

---

## 5. Trạng thái hiện tại

Backend hiện tại đã có cấu trúc nền để tiếp tục phát triển các chức năng chính.

Tuy nhiên, các chức năng nghiệp vụ chính vẫn chưa hoàn thiện:

* Chưa tạo database schema bằng Alembic.
* Chưa có bảng PostgreSQL chính thức.
* Chưa hoàn thiện API upload lưu database.
* Chưa có processing job thật.
* Chưa có worker xử lý file thật.
* Chưa có Trust Score pipeline thật.
* Chưa có report export thật.

---

## 6. Công việc tiếp theo

Các bước tiếp theo đề xuất:

1. Kiểm tra lại FastAPI chạy được tại `/docs`.
2. Tạo API upload local để backend và frontend có thể chạy song song.
3. Tạo model `User` chuẩn SQLAlchemy.
4. Cấu hình Alembic để nhận `Base.metadata`.
5. Tạo migration đầu tiên cho bảng `users`.
6. Chạy `alembic upgrade head`.
7. Kiểm tra PostgreSQL đã nhận bảng.
8. Tiếp tục tạo các bảng cốt lõi: `courses`, `classes`, `assignments`, `files`, `submissions`, `processing_jobs`.

---

## 7. Ghi chú kỹ thuật

* Không commit file `.env` vì có thể chứa mật khẩu PostgreSQL.
* Không commit thư mục `.venv`.
* Không commit thư mục `uploads/` và `exports/`.
* Các file trong `processing/` hiện mới là skeleton, chưa có logic xử lý đầy đủ.
* Các file trong `models/` hiện cần được bổ sung class SQLAlchemy trước khi migration.
* Cấu trúc hiện tại ưu tiên khả năng mở rộng và bảo trì cho MVP.
