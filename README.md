# 🧩 Patches

LinkedIn 게임 **Patches**를 다시 플레이하고 기록할 수 있는 웹사이트입니다.

## 소개

[Patches](https://www.linkedin.com/games/patches/)는 LinkedIn에서 제공하는 퍼즐 게임입니다. 하루에 한 번만 플레이할 수 있기 때문에, 이전 문제를 다시 풀어보거나 연습하기 어렵습니다.

이 프로젝트는 **과거 Patches 문제를 다시 플레이**하고, **플레이 기록을 저장**하여 볼 수 있도록 만든 웹 애플리케이션입니다.

## 주요 기능

- 🎮 과거 Patches 문제 다시 플레이
- 📊 플레이 기록 저장 및 조회
- 🔄 이전 기록과 비교하여 실력 향상 추적

## 기술 스택

| Category        | Technology              |
| --------------- | ----------------------- |
| Framework       | Next.js 16 (App Router) |
| Language        | TypeScript              |
| UI Library      | React 19                |
| Styling         | Tailwind CSS v4         |
| Package Manager | pnpm                    |

## 시작하기

### 사전 요구 사항

- [Node.js](https://nodejs.org/) 18.x 이상
- [pnpm](https://pnpm.io/) 10.x 이상

### 설치 및 실행

```bash
# 의존성 설치
pnpm install

# 개발 서버 실행
pnpm dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 열어 확인합니다.

## 프로젝트 구조

```
patches/
├── app/                # Next.js App Router (라우팅/레이아웃)
│   ├── (main)/         # 메인 라우트 그룹
│   ├── globals.css     # 글로벌 스타일
│   ├── layout.tsx      # Root Layout
│   └── page.tsx        # 홈 페이지
├── components/         # 공유 UI 컴포넌트
│   ├── ui/             # 범용 UI 프리미티브
│   └── layout/         # 앱 레이아웃 컴포넌트
├── features/           # 기능(도메인) 단위 모듈 (Colocation 원칙)
│   ├── game/           # 게임 플레이 기능
│   └── history/        # 기록 관리 기능
├── lib/                # 유틸리티 및 전역 상수
├── types/              # 전역 타입 정의
├── public/             # 정적 파일
├── .prettierrc         # Prettier 설정
├── eslint.config.mjs   # ESLint 설정
├── next.config.ts      # Next.js 설정
├── postcss.config.mjs  # PostCSS 설정
└── tsconfig.json       # TypeScript 설정
```

## 라이선스

This project is for personal use.
