# Patches 프로젝트 API 흐름 요약

## 1. 프로젝트 개요

이 프로젝트는 LinkedIn **Patches 퍼즐 스크린샷**을 업로드하고, OpenCV로 퍼즐 보드 영역을 추출한 뒤, 나중에 `.patches` 파일로 저장하기 위한 FastAPI 백엔드입니다.

현재 구현 범위는 **이미지 업로드 + 보드 영역 crop 추출**까지입니다.

아직 실제 OCR, 셀 문자 추출, patch size/shape 추출, 최종 `.patches` 저장 API는 구현되지 않았습니다.

---

## 2. 전체 API 흐름

```text
GET /health
  서버 상태 확인

POST /uploads
  이미지 + 퍼즐번호 + 보드크기 업로드
  → 이미지 파일 저장
  → uploads DB row 생성

POST /extractions/{upload_id}
  저장된 이미지 읽기
  → OpenCV로 보드 영역 탐지
  → board.png artifact 저장
  → extraction_jobs DB row 생성

GET /extractions/{job_id}
  추출 작업 결과 조회
```

---

## 3. API별 역할

### `GET /health`

파일: `backend/app/api/health.py`

서버가 살아있는지 확인합니다.

응답:

```json
{"status": "ok"}
```

---

### `POST /uploads`

파일: `backend/app/api/uploads.py`

사용자가 업로드한 스크린샷과 퍼즐 메타데이터를 저장합니다.

입력:

- `puzzle_number`: 퍼즐 번호
- `board_width`: 보드 가로 크기
- `board_height`: 보드 세로 크기
- `image`: 업로드 이미지

처리 흐름:

```text
content_type 검사
  → upload_id 생성
  → storage/uploads/ 에 이미지 저장
  → uploads DB row 저장
  → UploadResponse 반환
```

허용 이미지 타입:

- `image/png`
- `image/jpeg`
- `image/webp`

---

### `POST /extractions/{upload_id}`

파일: `backend/app/api/extractions.py`

업로드된 이미지에서 퍼즐 보드 영역을 찾고 crop 이미지를 저장합니다.

처리 흐름:

```text
upload_id로 Upload 조회
  → 이미지 파일 경로 확인
  → extract_board() 호출
  → board.png 저장
  → ExtractionJob 저장
  → 결과 반환
```

성공하면 `status = completed`, 실패하면 `status = failed`입니다.

현재 생성되는 `PuzzleDraft`는 빈 보드입니다. 실제 OCR 결과가 아닙니다.

---

### `GET /extractions/{job_id}`

파일: `backend/app/api/extractions.py`

이전에 실행한 추출 작업 결과를 조회합니다.

조회 내용:

- 작업 ID
- 업로드 ID
- 상태
- 보드 크기
- confidence
- board bbox
- crop 이미지 경로
- debug artifact 정보

---

## 4. 주요 파일별 용도

### 앱/설정

| 파일 | 용도 |
| --- | --- |
| `backend/app/main.py` | FastAPI 앱 생성, router 연결 |
| `backend/app/config.py` | DB URL, storage 경로 등 설정 |
| `backend/app/db.py` | SQLAlchemy engine/session 설정 |

---

### API 라우터

| 파일 | 용도 |
| --- | --- |
| `backend/app/api/health.py` | 서버 상태 확인 API |
| `backend/app/api/uploads.py` | 이미지 업로드 API |
| `backend/app/api/extractions.py` | 보드 추출/조회 API |

---

### DB 모델

| 파일 | 용도 |
| --- | --- |
| `backend/app/models/upload.py` | 업로드 이미지 메타데이터 저장 |
| `backend/app/models/extraction_job.py` | 보드 추출 작업 결과 저장 |
| `backend/app/models/saved_puzzle.py` | 최종 `.patches` 저장 정보 모델 |

---

### Schema

| 파일 | 용도 |
| --- | --- |
| `backend/app/schemas/upload.py` | 업로드 API 응답 구조 |
| `backend/app/schemas/extraction.py` | 추출 API 응답/debug artifact 구조 |
| `backend/app/schemas/puzzle.py` | 퍼즐 draft, patch definition, validation issue 구조 |

---

### CV/이미지 처리

| 파일 | 용도 |
| --- | --- |
| `backend/app/services/cv_extract.py` | 보드 추출 전체 흐름 |
| `backend/app/services/image_preprocess.py` | grayscale, blur, contrast, edge, mask 전처리 |
| `backend/app/services/layout_detect.py` | contour 기반 보드 후보 탐지/crop |
| `backend/app/services/grid_detect.py` | grid line 탐지 및 expected grid score 계산 |

---

### `.patches` 처리

| 파일 | 용도 |
| --- | --- |
| `backend/app/services/parse_patches.py` | `.patches` 텍스트를 `PuzzleDraft`로 변환 |
| `backend/app/services/serialize_patches.py` | `PuzzleDraft`를 `.patches` 텍스트로 변환 |
| `backend/app/services/validate_patches.py` | 퍼즐 draft 유효성 검사 |
| `backend/app/services/path_builder.py` | 업로드 이미지와 `.patches` 저장 경로 생성 |

---

## 5. CV 추출 내부 흐름

시작 함수: `backend/app/services/cv_extract.py`의 `extract_board()`

```text
image_path 입력
  → load_image()
  → image_preprocess 단계 실행
  → layout_detect로 보드 후보 탐지
  → 가장 점수 높은 후보 선택
  → perspective transform 또는 bbox crop
  → artifacts/{job_id}/board.png 저장
  → BoardExtractionResult 반환
```

Debug 모드에서는 중간 이미지도 저장합니다.

저장되는 debug artifact 예:

- grayscale image
- blurred image
- enhanced image
- sharpened image
- edges image
- board mask image
- contour overlay
- selected bbox overlay

---

## 6. `.patches` 파일 형식

예시:

```text
5x5
..a..
.....
b.c.d
.....
..e..
a:5:wide
b:8:tall
c:-:tall
```

의미:

- 첫 줄: 보드 크기
- 다음 줄들: 보드 배치
- 이후 줄들: patch 정의
- `-`: size unknown

허용 shape:

- `wide`
- `tall`
- `square`
- `any`

---

## 7. 현재 되는 것

- FastAPI 앱 실행 구조
- 서버 health check
- 이미지 업로드
- 이미지 파일 저장
- 업로드 메타데이터 DB 저장
- OpenCV 기반 보드 영역 crop
- debug artifact 저장
- 추출 작업 DB 저장
- `.patches` parse/serialize/validate
- pytest 23개 통과

---

## 8. 아직 안 되는 것

- 실제 OCR
- 보드 셀 문자 추출
- patch size/shape 추출
- 추출 결과를 실제 `.patches` draft로 채우기
- review flow API
- 최종 `.patches` 저장 API
- saved puzzle 조회 API

---

## 9. 주의할 점

- 현재 extraction은 `board.png` crop까지만 수행합니다.
- `normalized_draft_json`은 빈 보드 draft입니다.
- Alembic migration과 SQLAlchemy model 사이에 일부 불일치가 있습니다.
- `backend/app/api/uploads.py`에서 `Base.metadata.create_all(bind=engine)`가 import 시 실행됩니다. Alembic과 함께 운영할 경우 정리 필요합니다.

---

## 10. 한 줄 요약

현재 프로젝트는 **Patches 스크린샷을 업로드하고, 퍼즐 보드 영역만 잘라내는 FastAPI 백엔드**입니다.

다음 큰 단계는 **잘라낸 보드 이미지에서 셀/문자/patch 정보를 추출해 `.patches` draft를 만드는 것**입니다.
