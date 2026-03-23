# Backend

이 폴더는 LinkedIn Patches 스크린샷 업로드, OCR 추출, 리뷰, `.patches` 저장 흐름을 위한 백엔드 작업 공간입니다.

현재는 구현 코드를 넣기 전에 **리뷰 파일 저장 위치**, **업로드/생성 파일 저장 위치**, **권장 DB 테이블 구조**를 먼저 정의합니다.

## 목표

백엔드는 아래 흐름을 담당합니다.

1. 웹페이지에서 스크린샷과 퍼즐 번호(예: `22`) 업로드
2. 원본 이미지와 번호 메타데이터 저장
3. OCR/비전 파이프라인으로 퍼즐 draft 추출
4. 리뷰가 필요하면 리뷰 문서를 생성해 검수 대기 상태로 저장
5. 리뷰 중간 산출물이 필요하면 `<번호>-<생성순번>.patches` 형식으로 임시 생성
6. 검수 승인 후 최종 `.patches` 파일을 `<번호>.patches` 형식으로 저장

---

## 디렉터리 구조

```text
backend/
├── README.md
├── reviews/
│   ├── pending/
│   ├── approved/
│   └── rejected/
└── storage/
    ├── uploads/
    └── generated-patches/
```

### `reviews/`

리뷰 단계에서 생성되는 Markdown 파일을 저장하는 폴더입니다.

- `reviews/pending/`
  - OCR 결과가 검토 대기 상태인 리뷰 파일 저장
- `reviews/approved/`
  - 승인 완료된 리뷰 파일 저장
- `reviews/rejected/`
  - 반려된 리뷰 파일 저장

### `storage/uploads/`

사용자가 업로드한 원본 스크린샷을 저장합니다.

권장 파일명 형식:

- `{upload_id}.png`
- 예: `upl_20260409_001.png`

### `storage/generated-patches/`

리뷰 중간 산출물과 최종 승인된 `.patches` 파일을 저장합니다.

권장 파일명 형식:

- 리뷰 중 임시 생성 파일이 필요한 경우: `<번호>-<생성순번>.patches`
- 최종 승인 파일: `<번호>.patches`
- 예: `22-1.patches`, `22-2.patches`, `22.patches`

웹페이지에서는 `#` 없이 번호만 입력받는 것을 기준으로 합니다.
즉 업로드 시 `22`를 받으면 최종 파일은 `22.patches`로 저장합니다.

---

## 리뷰 Markdown 파일 형식

리뷰는 사람이 빠르게 확인하고 수정할 수 있어야 하므로, 파일 기반 검토가 필요하면 Markdown 형식이 적합합니다.

권장 위치:

- `backend/reviews/pending/{review_id}.md`

권장 예시:

````md
---
review_id: rev_20260409_001
upload_id: upl_20260409_001
puzzle_number: "22"
status: pending
created_at: 2026-04-09T09:00:00Z
image_path: backend/storage/uploads/upl_20260409_001.png
candidate_patches_path: backend/storage/generated-patches/22-1.patches
overall_confidence: 0.82
requires_review: true
---

# Review Summary

- OCR 결과에 불확실성이 있어 수동 검토가 필요합니다.
- 주요 이슈: LOW_CONFIDENCE_SIZE, BOARD_ID_MISMATCH

## Extraction Issues

- LOW_CONFIDENCE_SIZE: patch `c`의 크기 인식 신뢰도가 낮음
- BOARD_ID_MISMATCH: 보드의 ID 목록과 추출된 patch definition 목록이 다름

## Draft Puzzle

### Grid Size

`5x5`

### Board Layout

```text
..a..
.....
b.c.d
.....
..e..
```
````

### Patch Definitions

| ID  | Row | Col | Size | Shape  | Confidence |
| --- | --- | --- | ---- | ------ | ---------- |
| a   | 0   | 2   | 5    | wide   | 0.97       |
| b   | 2   | 0   | 8    | tall   | 0.94       |
| c   | 2   | 2   | ?    | tall   | 0.61       |
| d   | 2   | 4   | 4    | square | 0.93       |
| e   | 4   | 2   | 6    | wide   | 0.92       |

## Reviewer Decision

- [ ] Approve as-is
- [ ] Edit and approve
- [ ] Reject

## Reviewer Notes

- `c`의 size를 재확인 필요
- shape 값은 모두 유효함

````

### 이 형식을 추천하는 이유
- 사람이 읽기 쉽습니다.
- OCR 결과와 이슈를 한 문서에서 같이 볼 수 있습니다.
- 승인/반려 시 상태 변경이 명확합니다.
- 나중에 UI가 생겨도 같은 구조를 JSON/DB로 대응하기 쉽습니다.

---

## 권장 DB 테이블 구조

파일만으로도 시작할 수 있지만, 실제 서비스 흐름을 위해서는 DB 테이블이 필요합니다.

초기 기준으로는 SQLite 또는 PostgreSQL에서 아래 4개 테이블이면 충분합니다.

### 1. `uploads`
업로드 원본 이미지 메타데이터 저장

| Column | Type | Description |
|---|---|---|
| id | text PK | 업로드 ID |
| puzzle_number | integer | 웹페이지에서 입력받은 퍼즐 번호 |
| original_filename | text | 원본 파일명 |
| content_type | text | MIME type |
| file_path | text | 저장 경로 |
| file_size | integer | 파일 크기 |
| created_at | datetime | 업로드 시각 |

예시 레코드:

```json
{
  "id": "upl_20260409_001",
  "puzzle_number": 22,
  "original_filename": "patches-screenshot.png",
  "content_type": "image/png",
  "file_path": "backend/storage/uploads/upl_20260409_001.png",
  "file_size": 381244,
  "created_at": "2026-04-09T09:00:00Z"
}
````

### 2. `extraction_jobs`

OCR/비전 추출 작업 상태 저장

| Column                | Type      | Description                                                                 |
| --------------------- | --------- | --------------------------------------------------------------------------- |
| id                    | text PK   | 작업 ID                                                                     |
| upload_id             | text FK   | 업로드 ID                                                                   |
| candidate_sequence    | integer   | 같은 번호에서 생성된 임시 `.patches` 순번                                   |
| candidate_file_path   | text      | 임시 `.patches` 파일 경로                                                   |
| status                | text      | uploaded / processing / needs_review / approved / rejected / saved / failed |
| overall_confidence    | real      | 전체 신뢰도                                                                 |
| raw_result_json       | json/text | OCR/비전 파이프라인의 저수준 원본 결과                                      |
| normalized_draft_json | json/text | 리뷰/검증/UI용으로 정규화한 중간 draft                                      |
| created_at            | datetime  | 생성 시각                                                                   |
| updated_at            | datetime  | 수정 시각                                                                   |

`raw_result_json`은 OCR 엔진과 비전 파이프라인이 만든 원본 결과를 저장합니다.
이 값은 디버깅, 재처리, 인식 실패 원인 분석을 위한 용도이며, bounding box, 원본 OCR text, stage별 confidence 같은 저수준 데이터를 담습니다.

예시 `raw_result_json`:

```json
{
  "board_detection": {
    "grid_size_candidate": { "width": 5, "height": 5, "confidence": 0.94 },
    "cells": [
      { "row": 0, "col": 2, "text": "a", "confidence": 0.98 },
      { "row": 2, "col": 0, "text": "b", "confidence": 0.97 }
    ]
  },
  "clue_ocr": {
    "patches": [
      { "id": "a", "size_text": "5", "shape_text": "wide", "confidence": 0.93 },
      { "id": "c", "size_text": "?", "shape_text": "tall", "confidence": 0.61 }
    ]
  },
  "artifacts": {
    "board_crop_path": "backend/storage/uploads/upl_20260409_001-board.png",
    "clue_crop_path": "backend/storage/uploads/upl_20260409_001-clue.png"
  }
}
```

`normalized_draft_json`은 최종 `.patches`를 만들기 직전의 정규화 데이터입니다.
이 값은 `.patches` 텍스트 자체가 아니라, 리뷰 중 필드 단위 수정과 validator 적용이 쉬운 구조화 데이터로 유지합니다.
즉 최종 저장 포맷은 `.patches`지만, 중간 검토 포맷은 JSON으로 두는 것이 기준입니다.

예시 `normalized_draft_json`:

```json
{
  "width": 5,
  "height": 5,
  "board_rows": ["..a..", ".....", "b.c.d", ".....", "..e.."],
  "patches": [
    { "id": "a", "row": 0, "col": 2, "size": 5, "shape": "wide" },
    { "id": "b", "row": 2, "col": 0, "size": 8, "shape": "tall" },
    { "id": "c", "row": 2, "col": 2, "size": null, "shape": "tall" },
    { "id": "d", "row": 2, "col": 4, "size": 4, "shape": "square" },
    { "id": "e", "row": 4, "col": 2, "size": 6, "shape": "wide" }
  ]
}
```

### 3. `review_records`

리뷰 문서 및 검수 결과 저장

| Column              | Type              | Description                              |
| ------------------- | ----------------- | ---------------------------------------- |
| id                  | text PK           | 리뷰 ID                                  |
| extraction_job_id   | text FK           | 추출 작업 ID                             |
| status              | text              | pending / approved / rejected            |
| markdown_path       | text              | 리뷰 Markdown 파일 경로                  |
| candidate_file_path | text nullable     | 리뷰 중 생성된 임시 `.patches` 파일 경로 |
| issues_json         | json/text         | 검토 이슈 목록                           |
| reviewer_notes      | text              | 검수 메모                                |
| reviewed_at         | datetime nullable | 검수 완료 시각                           |
| created_at          | datetime          | 생성 시각                                |

예시 `issues_json`:

```json
[
  {
    "code": "LOW_CONFIDENCE_SIZE",
    "field": "patches.c.size",
    "severity": "warning"
  },
  { "code": "BOARD_ID_MISMATCH", "field": null, "severity": "error" }
]
```

### 4. `saved_puzzles`

최종 저장된 퍼즐 파일 정보

| Column            | Type     | Description                      |
| ----------------- | -------- | -------------------------------- |
| id                | text PK  | 퍼즐 ID                          |
| puzzle_number     | integer  | 최종 파일명에 사용되는 퍼즐 번호 |
| extraction_job_id | text FK  | 원본 추출 작업 ID                |
| review_record_id  | text FK  | 승인된 리뷰 ID                   |
| patches_file_path | text     | 최종 `<번호>.patches` 저장 경로  |
| patches_content   | text     | 저장된 `.patches` 본문           |
| created_at        | datetime | 저장 시각                        |

---

## 권장 상태 흐름

```text
uploads
  -> uploads.puzzle_number 저장
  -> extraction_jobs.status = uploaded
  -> extraction_jobs.status = processing
  -> 필요 시 extraction_jobs.candidate_sequence 증가
  -> 필요 시 `<번호>-<생성순번>.patches` 임시 생성
  -> extraction_jobs.status = needs_review
  -> review_records.status = pending
  -> review_records.status = approved | rejected
  -> extraction_jobs.status = approved | rejected
  -> 승인 시 `<번호>.patches` 최종 생성
  -> saved_puzzles 생성
  -> extraction_jobs.status = saved
```

---

## 왜 파일 + DB를 같이 두는가

둘 중 하나만 써도 되지만, 초기 백엔드에는 둘을 같이 두는 구성이 실용적입니다.

- **Markdown 파일**: 사람이 직접 검토하기 쉽고, 운영 중 임시 검수 자료로 유용함
- **DB 테이블**: 상태 관리, API 응답, 검색, 목록 조회에 유리함

권장 방침:

- **DB를 기준 데이터 저장소로 사용**
- **Markdown은 검수용 파생 산출물로 저장**

즉, 실제 상태 판정은 DB가 담당하고, 리뷰 문서는 사람이 보기 좋은 형태로 함께 저장합니다.

---

## 다음 구현 우선순위

1. `backend/app/` 생성
2. `uploads`, `extraction_jobs`, `review_records`, `saved_puzzles` 모델 작성
3. `.patches` validator / serializer 작성
4. 리뷰 Markdown 생성기 작성
5. 업로드 → 추출 → 리뷰 → 저장 API 작성
