# TrustLens Backend API Documents

Last updated: 2026-06-20

## Overview

TrustLens Backend is a FastAPI service for managing academic reference verification workflows:

- Authentication and current user profile.
- Courses, classes, and assignments.
- Submission upload and processing.
- Citation extraction, metadata verification, scoring, report generation, and report export.

Default API base path:

```text
http://localhost:8000/api/v1
```

FastAPI interactive docs:

```text
http://localhost:8000/docs
```

## Authentication

Most endpoints require a JWT access token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

Roles used by the API:

| Role | Meaning |
| --- | --- |
| `ADMIN` | Can access all lecturer-scoped resources. |
| `LECTURER` | Can access resources that belong to classes they own. |
| `STUDENT` | Currently not used by the mounted v1 endpoints except where a future dependency allows it. |

Common authentication and authorization errors:

| HTTP Status | Typical error_code | Meaning |
| --- | --- | --- |
| `401` | `AUTH_REQUIRED` | Missing bearer token. |
| `401` | `AUTH_INVALID_TOKEN` | Invalid or expired access token. |
| `403` | `AUTH_ROLE_FORBIDDEN` | User role is not allowed. |
| `403` | `AUTH_OWNERSHIP_FORBIDDEN` | User cannot access a resource owned by another lecturer. |

Standard error body:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message.",
  "details": {}
}
```

## Endpoint Summary

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | Health check. |
| `POST` | `/auth/register` | Public | Register a new user. |
| `POST` | `/auth/login` | Public | Login and receive tokens. |
| `POST` | `/auth/refresh` | Public | Exchange refresh token for a new access token. |
| `GET` | `/users/me` | Bearer | Read current user profile. |
| `POST` | `/courses` | Lecturer/Admin | Create a course. |
| `GET` | `/courses` | Lecturer/Admin | List courses. |
| `POST` | `/classes` | Lecturer/Admin | Create a class. |
| `GET` | `/classes` | Lecturer/Admin | List accessible classes. |
| `POST` | `/assignments` | Lecturer/Admin | Create an assignment. |
| `GET` | `/assignments` | Lecturer/Admin | List accessible assignments. |
| `POST` | `/submissions/upload` | Lecturer/Admin | Upload a submission file. |
| `POST` | `/submissions/{submission_id}/analyze` | Lecturer/Admin | Start text extraction / analysis job. |
| `POST` | `/submissions/{submission_id}/detect-references` | Lecturer/Admin | Detect reference section. |
| `POST` | `/submissions/{submission_id}/parse-citations` | Lecturer/Admin | Parse citations from reference section. |
| `POST` | `/submissions/{submission_id}/verify-metadata` | Lecturer/Admin | Verify citation metadata. |
| `GET` | `/jobs/{job_id}` | Lecturer/Admin | Read job status. |
| `GET` | `/jobs/submissions/{submission_id}/latest` | Lecturer/Admin | Read latest job for a submission. |
| `POST` | `/jobs/submissions/{submission_id}/process` | Lecturer/Admin | Queue full submission processing pipeline. |
| `POST` | `/jobs/{job_id}/retry` | Lecturer/Admin | Retry a failed processing job. |
| `GET` | `/reports/submissions/{submission_id}` | Lecturer/Admin | Read submission report. |
| `POST` | `/reports/submissions/{submission_id}/generate` | Lecturer/Admin | Generate/read submission report. |
| `GET` | `/reports/submissions/{submission_id}/export/docx` | Lecturer/Admin | Export report as DOCX. |
| `GET` | `/reports/submissions/{submission_id}/export/pdf` | Lecturer/Admin | Export report as PDF. |
| `GET` | `/reports/submissions/{submission_id}/export/xlsx` | Lecturer/Admin | Export report as XLSX. |

Note: `admin.py` and `report_exports.py` endpoint files exist in the codebase, but they are not currently included in `app/api/v1/api_router.py`.

## Data Models

### UserRead

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Nguyen Van A",
  "role": "LECTURER",
  "is_active": true,
  "created_at": "2026-06-20T00:00:00Z"
}
```

### Course

Create:

```json
{
  "code": "CS101",
  "name": "Introduction to Computer Science",
  "description": "Optional description"
}
```

Read:

```json
{
  "id": "uuid",
  "code": "CS101",
  "name": "Introduction to Computer Science",
  "description": "Optional description",
  "created_at": "2026-06-20T00:00:00Z"
}
```

### Class

Create:

```json
{
  "course_id": "uuid",
  "class_code": "CS101-01",
  "name": "CS101 - Group 01",
  "term_name": "2026-S1"
}
```

Read:

```json
{
  "id": "uuid",
  "course_id": "uuid",
  "lecturer_id": "uuid",
  "class_code": "CS101-01",
  "name": "CS101 - Group 01",
  "term_name": "2026-S1",
  "created_at": "2026-06-20T00:00:00Z"
}
```

### Assignment

Create:

```json
{
  "class_id": "uuid",
  "title": "Final Essay",
  "description": "Upload final academic essay.",
  "required_style": "APA",
  "status": "OPEN"
}
```

Read:

```json
{
  "id": "uuid",
  "class_id": "uuid",
  "title": "Final Essay",
  "description": "Upload final academic essay.",
  "required_style": "APA",
  "status": "OPEN",
  "created_at": "2026-06-20T00:00:00Z"
}
```

### SubmissionUploadResponse

```json
{
  "message": "Upload file successfully.",
  "submission": {
    "id": "uuid",
    "assignment_id": "uuid",
    "file_id": "uuid",
    "owner_label": "Student A",
    "status": "UPLOADED",
    "overall_score": null,
    "created_at": "2026-06-20T00:00:00Z"
  },
  "file": {
    "id": "uuid",
    "original_name": "essay.pdf",
    "stored_name": "uuid.pdf",
    "stored_path": "uploads/uuid.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 123456,
    "checksum": "sha256...",
    "uploaded_by": "uuid",
    "created_at": "2026-06-20T00:00:00Z"
  },
  "job": {
    "id": "uuid",
    "submission_id": "uuid",
    "status": "QUEUED",
    "progress": 0,
    "step": "queued",
    "current_step": "queued",
    "report_id": null,
    "retry_of_job_id": null,
    "error_code": null,
    "error_message": null,
    "error_details": null,
    "started_at": null,
    "finished_at": null,
    "updated_at": null,
    "created_at": "2026-06-20T00:00:00Z"
  }
}
```

### JobRead

```json
{
  "id": "uuid",
  "submission_id": "uuid",
  "status": "QUEUED",
  "progress": 0,
  "step": "queued",
  "current_step": "queued",
  "report_id": null,
  "retry_of_job_id": null,
  "error_code": null,
  "error_message": null,
  "error_details": null,
  "started_at": null,
  "finished_at": null,
  "updated_at": null,
  "created_at": "2026-06-20T00:00:00Z"
}
```

### SubmissionReportResponse

```json
{
  "message": "Report fetched successfully.",
  "submission": {
    "id": "uuid",
    "assignment_id": "uuid",
    "file_id": "uuid",
    "owner_label": "Student A",
    "status": "COMPLETED",
    "overall_score": 82.5,
    "created_at": "2026-06-20T00:00:00Z",
    "updated_at": null
  },
  "file": {
    "id": "uuid",
    "original_name": "essay.pdf",
    "stored_name": "uuid.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 123456,
    "checksum": "sha256...",
    "uploaded_by": "uuid",
    "created_at": "2026-06-20T00:00:00Z"
  },
  "extracted_document": {
    "id": "uuid",
    "word_count": 2500,
    "page_count": 8,
    "extraction_method": "pdf",
    "status": "COMPLETED",
    "created_at": "2026-06-20T00:00:00Z"
  },
  "reference_section": {
    "id": "uuid",
    "heading": "References",
    "start_index": 1000,
    "end_index": 2500,
    "detection_method": "heuristic",
    "raw_text_preview": "..."
  },
  "summary": {
    "processing": {
      "submission_status": "COMPLETED",
      "has_extracted_text": true,
      "has_reference_section": true,
      "citation_count": 12,
      "metadata_record_count": 12,
      "latest_job": {
        "id": "uuid",
        "status": "COMPLETED",
        "progress": 100,
        "step": "completed",
        "error_code": null,
        "created_at": "2026-06-20T00:00:00Z",
        "updated_at": "2026-06-20T00:01:00Z"
      }
    },
    "verification": {
      "total": 12,
      "verified": 8,
      "basic_metadata_present": 10,
      "broken": 1,
      "forbidden": 0,
      "unreachable": 1,
      "not_provided": 2
    },
    "score": {
      "overall_score": 82.5,
      "trust_level": "high",
      "note": null
    }
  },
  "citations": [
    {
      "citation": {
        "id": "uuid",
        "sequence_no": 1,
        "raw_text": "Author. (2024). Title...",
        "detected_style": "APA",
        "authors": "Author",
        "title": "Title",
        "year": 2024,
        "doi": "10.xxxx/yyyy",
        "url": "https://example.com"
      },
      "metadata": {
        "id": "uuid",
        "provider": "Crossref",
        "query_type": "doi",
        "query_value": "10.xxxx/yyyy",
        "source_url": "https://doi.org/10.xxxx/yyyy",
        "matched_title": "Title",
        "matched_year": 2024,
        "verification_status": "ACADEMIC_VERIFIED",
        "confidence_score": 0.95,
        "raw_response": {}
      },
      "warnings": [],
      "score": 95,
      "trust_level": "high"
    }
  ]
}
```

## Endpoints

### GET /health

Health check.

Response `200`:

```json
{
  "status": "ok",
  "service": "TrustLens Backend"
}
```

### POST /auth/register

Register a new user.

Auth: public.

Request body:

```json
{
  "full_name": "Nguyen Van A",
  "email": "lecturer@example.com",
  "password": "secret123"
}
```

Response `201`:

```json
{
  "message": "Sign-up successful.",
  "user": {
    "id": "uuid",
    "email": "lecturer@example.com",
    "full_name": "Nguyen Van A",
    "role": "LECTURER",
    "is_active": true,
    "created_at": "2026-06-20T00:00:00Z"
  }
}
```

Errors:

| Status | error_code | Meaning |
| --- | --- | --- |
| `409` | `AUTH_EMAIL_ALREADY_EXISTS` | Email already registered. |
| `422` | `AUTH_FULL_NAME_REQUIRED` | Full name is empty. |
| `422` | `AUTH_WEAK_PASSWORD` | Password is shorter than required. |

### POST /auth/login

Login using email and password.

Auth: public.

Request body:

```json
{
  "email": "lecturer@example.com",
  "password": "secret123"
}
```

Response `200`:

```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "lecturer@example.com",
    "full_name": "Nguyen Van A",
    "role": "LECTURER",
    "is_active": true,
    "created_at": "2026-06-20T00:00:00Z"
  }
}
```

Errors:

| Status | error_code |
| --- | --- |
| `401` | `AUTH_INVALID_CREDENTIALS` |

### POST /auth/refresh

Create a new access token from a refresh token.

Auth: public.

Request body:

```json
{
  "refresh_token": "jwt-refresh-token"
}
```

Response `200`:

```json
{
  "access_token": "new-jwt-access-token",
  "token_type": "bearer"
}
```

Errors:

| Status | error_code |
| --- | --- |
| `401` | `AUTH_INVALID_REFRESH_TOKEN` |
| `401` | `AUTH_USER_NOT_FOUND` |

### GET /users/me

Read the authenticated user profile.

Auth: bearer token.

Response `200`: `UserRead`.

### POST /courses

Create a course.

Auth: `LECTURER` or `ADMIN`.

Request body: `CourseCreate`.

Response `201`: `CourseRead`.

Errors:

| Status | error_code |
| --- | --- |
| `409` | `COURSE_CODE_EXISTS` |

### GET /courses

List courses.

Auth: `LECTURER` or `ADMIN`.

Response `200`:

```json
[
  {
    "id": "uuid",
    "code": "CS101",
    "name": "Introduction to Computer Science",
    "description": "Optional description",
    "created_at": "2026-06-20T00:00:00Z"
  }
]
```

### POST /classes

Create a class for the authenticated lecturer.

Auth: `LECTURER` or `ADMIN`.

Request body: `ClassCreate`.

Response `201`: `ClassRead`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `COURSE_NOT_FOUND` |
| `409` | `CLASS_CODE_EXISTS` |

### GET /classes

List accessible classes.

Auth: `LECTURER` or `ADMIN`.

Behavior:

- `ADMIN` receives all classes.
- `LECTURER` receives only classes where `lecturer_id` equals the current user id.

Response `200`: array of `ClassRead`.

### POST /assignments

Create an assignment inside a class.

Auth: `LECTURER` or `ADMIN`.

Ownership:

- `ADMIN` can create in any class.
- `LECTURER` can create only in classes they own.

Request body: `AssignmentCreate`.

Response `201`: `AssignmentRead`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `CLASS_NOT_FOUND` |
| `403` | `CLASS_OWNERSHIP_FORBIDDEN` |
| `409` | `ASSIGNMENT_TITLE_EXISTS` |

### GET /assignments

List accessible assignments.

Auth: `LECTURER` or `ADMIN`.

Query parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `class_id` | `UUID` | No | Filter assignments by class. |

Behavior:

- `ADMIN` can list all assignments, optionally filtered by `class_id`.
- `LECTURER` can list assignments for owned classes only.

Response `200`: array of `AssignmentRead`.

### POST /submissions/upload

Upload a submission file and create the first processing job.

Auth: `LECTURER` or `ADMIN`.

Content type:

```http
multipart/form-data
```

Form fields:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `assignment_id` | `UUID` | Yes | Target assignment. |
| `owner_label` | `string` | No | Free-text label for the submission owner/student. |
| `file` | `file` | Yes | Uploaded document. |

Response `201`: `SubmissionUploadResponse`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `ASSIGNMENT_NOT_FOUND` |
| `400` | `ASSIGNMENT_NOT_OPEN` |
| `403` | `AUTH_OWNERSHIP_FORBIDDEN` |

Example cURL:

```bash
curl -X POST "http://localhost:8000/api/v1/submissions/upload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "assignment_id=<assignment_uuid>" \
  -F "owner_label=Student A" \
  -F "file=@essay.pdf"
```

### POST /submissions/{submission_id}/analyze

Start text extraction / analysis for a submission.

Auth: `LECTURER` or `ADMIN`.

Path parameters:

| Name | Type |
| --- | --- |
| `submission_id` | `UUID` |

Response `202`: `AnalyzeJobResponse`.

```json
{
  "job_id": "uuid",
  "submission_id": "uuid",
  "status": "queued",
  "progress": 0,
  "created_at": "2026-06-20T00:00:00Z"
}
```

### POST /submissions/{submission_id}/detect-references

Detect the reference section for a submission.

Auth: `LECTURER` or `ADMIN`.

Response `200`: `DetectReferenceSectionResponse`.

Important response fields:

- `job`: current processing job.
- `reference_section`: detected section with heading, raw text, start/end indexes, and detection method.

### POST /submissions/{submission_id}/parse-citations

Parse citations from the detected reference section.

Auth: `LECTURER` or `ADMIN`.

Response `200`: `ParseCitationsResponse`.

Important response fields:

- `total`: number of parsed citations.
- `citations`: citation list with raw text and extracted metadata fields.

### POST /submissions/{submission_id}/verify-metadata

Verify parsed citations using metadata providers and URL/DOI checks.

Auth: `LECTURER` or `ADMIN`.

Response `200`: `VerifyMetadataResponse`.

Important summary fields:

| Field | Meaning |
| --- | --- |
| `total` | Total metadata records returned. |
| `verified` | Legacy count: academic verified + DOI OK. |
| `academic_verified` | Academic metadata confidently matched. |
| `academic_partial` | Partial academic match. |
| `academic_ambiguous` | Ambiguous academic match. |
| `academic_not_found` | Academic lookup attempted but not found. |
| `doi_ok` | DOI resolved successfully. |
| `url_ok` | URL reachable. |
| `url_broken` | URL appears broken. |
| `url_forbidden` | URL returned forbidden/access denied. |
| `url_unreachable` | URL could not be reached. |

### GET /jobs/{job_id}

Read a processing job.

Auth: `LECTURER` or `ADMIN`.

Response `200`: `JobRead`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `JOB_NOT_FOUND` |
| `403` | `AUTH_OWNERSHIP_FORBIDDEN` |

### GET /jobs/submissions/{submission_id}/latest

Read the latest processing job for a submission.

Auth: `LECTURER` or `ADMIN`.

Response `200`:

```json
{
  "message": "Latest submission job fetched successfully.",
  "submission_id": "uuid",
  "job": {
    "job_id": "uuid",
    "submission_id": "uuid",
    "status": "queued",
    "progress": 0,
    "current_step": "queued",
    "started_at": null,
    "updated_at": "2026-06-20T00:00:00Z",
    "completed_at": null,
    "report_id": null,
    "error": null
  }
}
```

### POST /jobs/submissions/{submission_id}/process

Queue the full submission processing pipeline.

Auth: `LECTURER` or `ADMIN`.

Response `202`: `JobProcessResponse`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `SUBMISSION_NOT_FOUND` |
| `409` | `ANALYSIS_ALREADY_COMPLETED` |

### POST /jobs/{job_id}/retry

Retry a failed processing job.

Auth: `LECTURER` or `ADMIN`.

Response `202`: `JobProcessResponse`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `JOB_NOT_FOUND` |
| `409` | `JOB_STILL_ACTIVE` |
| `409` | `JOB_ALREADY_COMPLETED` |
| `400` | `JOB_NOT_RETRYABLE` |

### GET /reports/submissions/{submission_id}

Read a submission report.

Auth: `LECTURER` or `ADMIN`.

Response `200`: `SubmissionReportResponse`.

Errors:

| Status | error_code |
| --- | --- |
| `404` | `SUBMISSION_NOT_FOUND` |
| `404` | `REPORT_NOT_FOUND` |
| `403` | `AUTH_OWNERSHIP_FORBIDDEN` |

### POST /reports/submissions/{submission_id}/generate

Generate or read the submission report.

Auth: `LECTURER` or `ADMIN`.

Current behavior calls the same report service as `GET /reports/submissions/{submission_id}`.

Response `200`: `SubmissionReportResponse`.

### GET /reports/submissions/{submission_id}/export/docx

Export the submission report as DOCX.

Auth: `LECTURER` or `ADMIN`.

Response `200`:

- `Content-Type`: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition`: attachment with generated filename.

### GET /reports/submissions/{submission_id}/export/pdf

Export the submission report as PDF.

Auth: `LECTURER` or `ADMIN`.

Response `200`:

- `Content-Type`: `application/pdf`
- `Content-Disposition`: attachment with generated filename.

### GET /reports/submissions/{submission_id}/export/xlsx

Export the submission report as XLSX.

Auth: `LECTURER` or `ADMIN`.

Response `200`:

- `Content-Type`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition`: attachment with generated filename.

## Recommended Workflow

1. Register or login:

```http
POST /api/v1/auth/login
```

2. Create a course:

```http
POST /api/v1/courses
```

3. Create a class under that course:

```http
POST /api/v1/classes
```

4. Create an assignment in the class:

```http
POST /api/v1/assignments
```

5. Upload a submission file:

```http
POST /api/v1/submissions/upload
```

6. Process the submission:

```http
POST /api/v1/jobs/submissions/{submission_id}/process
```

7. Poll job status:

```http
GET /api/v1/jobs/{job_id}
GET /api/v1/jobs/submissions/{submission_id}/latest
```

8. Read or export report:

```http
GET /api/v1/reports/submissions/{submission_id}
GET /api/v1/reports/submissions/{submission_id}/export/pdf
GET /api/v1/reports/submissions/{submission_id}/export/docx
GET /api/v1/reports/submissions/{submission_id}/export/xlsx
```

## Implementation Notes

- All mounted v1 endpoints live under `/api/v1`.
- CORS defaults to `http://localhost:5173` and also allows Vercel preview domains matching `https://*.vercel.app`.
- Upload limits are controlled by `MAX_UPLOAD_SIZE_MB` in backend settings.
- `ADMIN` bypasses lecturer ownership checks.
- `LECTURER` access is scoped through class ownership.
- Some endpoint files in `app/api/v1/endpoints` are not mounted until added to `api_router.py`.
