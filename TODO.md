# TODO

## 보드 이미지 추출 서버

- [x] `POST /puzzles` — 이미지 업로드 + 보드 영역 crop 단일 엔드포인트
- [x] CV 전처리 파이프라인 (grayscale → blur → CLAHE → sharpen → edge)
- [x] contour 기반 보드 후보 탐지 및 스코어링
- [ ] **OCR**: 잘라낸 보드 이미지에서 셀 영역 분할 및 문자 인식
- [ ] **셀 데이터 추출**: 개별 셀 이미지 → patch size/shape 분류
- [ ] **구조화된 JSON 응답**: `POST /puzzles` 가 cells 배열을 포함한 `PuzzleDraft` JSON 반환

```json
{
  "puzzle_number": 1,
  "board_width": 5,
  "board_height": 5,
  "status": "completed",
  "confidence": 0.92,
  "board_bbox": [120, 80, 600, 600],
  "cells": [
    { "id": "a", "row": 0, "col": 2, "size": 5, "shape": "wide", "confidence": 0.95 },
    { "id": "b", "row": 2, "col": 0, "size": 8, "shape": "tall", "confidence": 0.92 }
  ]
}
```

- [ ] **`.patches` 변환**: 위 JSON → `.patches` 텍스트 (기존 serialize_patches 활용)
- [ ] `GET /puzzles/{extract_id}` — 추출 결과 JSON 조회 API
- [ ] `GET /puzzles/{extract_id}/patches` — `.patches` 텍스트 다운로드 API
- [ ] 보드 탐지 실패 시 fallback / 재시도 로직

## 어드민 페이지 (직접 업로드)

- [ ] 스크린샷 업로드 + 퍼즐 번호/보드 크기 입력 폼
- [ ] 추출 결과 미리보기 (board.png + 셀 그리드 오버레이)
- [ ] 셀별 OCR 결과 표시 (ID, size, shape, confidence)
- [ ] `.patches` 미리보기 및 다운로드
- [ ] 추출 실패 시 에러 메시지 표시
- [ ] 진행 중 상태 표시 (로딩)

## 퍼즐 갤러리 페이지 (일반 사용자)

- [ ] LinkedIn Patches 게임 목록을 10 × N 그리드로 표시
- [ ] 각 퍼즐 썸네일 (board.png) + 번호 표시
- [ ] 퍼즐 클릭 → 상세 보기 (셀 정보, `.patches` 다운로드)
- [ ] `GET /puzzles` — 퍼즐 목록 조회 API (갤러리용)
