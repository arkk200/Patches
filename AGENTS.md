<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

<!-- END:nextjs-agent-rules -->

---

# Project Context: Patches

## Overview

**Patches**는 LinkedIn 관련 웹 애플리케이션 프로젝트입니다. 보드판을 겹치지 않는 직사각형 영역으로 나누는 퍼즐 게임인 **Shikaku(시카쿠)**를 기반으로 합니다.

상세한 게임 규칙은 [game_rules.md](./docs/game_rules.md)를 참고하세요.

현재 초기 단계로, Next.js 기반의 기본 프로젝트 구조가 세팅되어 있습니다.

## Tech Stack

| Category        | Technology                     | Version |
| --------------- | ------------------------------ | ------- |
| Framework       | Next.js (App Router)           | 16.2.0  |
| Language        | TypeScript                     | ^5      |
| UI Library      | React                          | 19.2.4  |
| Styling         | Tailwind CSS v4 (PostCSS 방식) | ^4      |
| Linting         | ESLint (Flat Config)           | ^9      |
| Formatting      | Prettier                       | ^3.8.1  |
| Package Manager | pnpm                           | 10.x    |

## Conventions

### Code Style

- **Prettier**: `.prettierrc` 참고
  - 세미콜론 없음 (`semi: false`)
  - 싱글 쿼트 (`singleQuote: true`, `jsxSingleQuote: true`)
  - Trailing comma 사용 (`trailingComma: "all"`)
  - 줄 너비 100자 (`printWidth: 100`)
  - Tailwind CSS 클래스 자동 정렬 (`prettier-plugin-tailwindcss`)
- **ESLint**: `eslint.config.mjs` — `eslint-config-next/core-web-vitals` + `typescript` 사용
- **Auto Format on Save**: `.vscode/settings.json`에서 Prettier 자동 포맷 + import 자동 정리 설정

### Path Alias

- `@/*` → 프로젝트 루트 (`./`) 기준 (tsconfig.json)

### Package Manager

- **반드시 `pnpm`을 사용**할 것. `npm` 또는 `yarn` 사용 금지.

## Project Structure

```
patches/
├── app/                    # Next.js App Router (라우팅/레이아웃 레이어)
│   ├── (main)/             #   메인 페이지 그룹
│   │   ├── play/           #     게임 플레이 관련 페이지
│   │   └── history/        #     기록 조회 관련 페이지
│   ├── globals.css         # 글로벌 CSS
│   ├── layout.tsx          # Root Layout
│   └── page.tsx            # 홈 페이지
├── components/             # 공유 UI 컴포넌트
│   ├── ui/                 #   범용 UI 프리미티브 (Button, Card 등)
│   └── layout/             #   공용 레이아웃 컴포넌트 (Header, Footer 등)
├── features/               # 기능(도메인) 단위 모듈
│   ├── game/               #   게임 플레이 관련 비즈니스 로직 및 전용 컴포넌트
│   └── history/            #   기록 관리 관련 비즈니스 로직 및 전용 컴포넌트
├── lib/                    # 유틸리티 및 전역 상수
├── types/                  # 전역 타입 정의
├── public/                 # 정적 파일
├── .prettierrc             # Prettier 설정
├── eslint.config.mjs       # ESLint 설정
├── next.config.ts          # Next.js 설정
├── postcss.config.mjs      # PostCSS 설정
├── tsconfig.json           # TypeScript 설정
├── pnpm-workspace.yaml     # pnpm 워크스페이스 설정
├── package.json
└── AGENTS.md               # 이 파일 (AI 에이전트 컨텍스트)
```

## Styling

- **Tailwind CSS v4**를 PostCSS 플러그인 (`@tailwindcss/postcss`)으로 사용
- `globals.css`에서 `@import 'tailwindcss'`와 `@theme inline` 사용
- 커스텀 CSS 변수: `--background`, `--foreground` (다크모드 지원)
- 폰트: Geist Sans, Geist Mono (Google Fonts via `next/font`)

## Important Notes

- Next.js 16 사용 중 — API 및 파일 구조가 이전 버전과 다를 수 있음. 코드 작성 전 `node_modules/next/dist/docs/`의 가이드를 참고할 것.
- 프로젝트는 초기 단계이므로 아직 추가 라우트, 컴포넌트, API Route 등이 없음.
