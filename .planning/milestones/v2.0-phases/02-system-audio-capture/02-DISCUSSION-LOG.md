# Phase 2: System Audio Capture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 02-system-audio-capture
**Areas discussed:** BlackHole 설치 가이드, 오디오 소스 선택 UX, 듀얼 채널 합성, BlackHole 미설치 시 동작, 시스템 오디오 품질, 녹음 상태 표시, 에러 처리

---

## BlackHole 설치 가이드

| Option | Description | Selected |
|--------|-------------|----------|
| 인앱 위저드 | 앱 내에서 단계별 안내 + 외부 다운로드 링크 제공 | ✓ |
| 외부 링크만 | BlackHole GitHub 페이지로 안내 | |
| Homebrew 자동 설치 | 앱에서 brew install 실행 시도 | |

**User's choice:** 인앱 위저드
**Notes:** Homebrew 명령어 복사 버튼, 또는 BlackHole GitHub releases 페이지로 연결

## Aggregate Device 생성

| Option | Description | Selected |
|--------|-------------|----------|
| 자동 생성 | CoreAudio API (pyobjc)로 자동 생성 | ✓ |
| 수동 안내 | Audio MIDI Setup 여는 방법을 스크린샷과 함께 안내 | |
| You decide | Claude가 기술적 타당성 기반으로 결정 | |

**User's choice:** 자동 생성
**Notes:** 사용자가 Audio MIDI Setup을 열 필요 없어야 함

## 오디오 소스 선택 UX

| Option | Description | Selected |
|--------|-------------|----------|
| 토글 스위치 | 녹음 버튼 옆에 System Audio 토글 | ✓ |
| 드롭다운 메뉴 | 입력 소스 드롭다운: Mic Only / System / Both | |
| Preferences에서만 | 설정에서만 구성 가능 | |

**User's choice:** 토글 스위치
**Notes:** ON이면 마이크 + 시스템 동시 캡처

## BlackHole 미설치 시 토글 표시

| Option | Description | Selected |
|--------|-------------|----------|
| 비활성화 + 설치 안내 | 토글 보이지만 비활성화, 클릭하면 설치 위저드 | ✓ |
| 숨김 | BlackHole 없으면 UI 자체를 숨김 | |
| You decide | Claude가 UX 판단 | |

**User's choice:** 비활성화 + 설치 안내

## 듀얼 채널 합성

| Option | Description | Selected |
|--------|-------------|----------|
| 단일 믹스 | 두 오디오를 하나로 합쳐서 whisper에 전달 | ✓ |
| Aggregate Device 사용 | macOS Aggregate Device가 하드웨어 레벨에서 합침 | |
| You decide | Claude가 기술적으로 최적의 방법 선택 | |

**User's choice:** 단일 믹스

## BlackHole 미설치 시 동작

| Option | Description | Selected |
|--------|-------------|----------|
| 마이크 전용 모드 | 기존과 동일하게 마이크만으로 정상 작동 | ✓ |
| 시작 시 설치 권유 | 앱 첫 실행 시 설치 권유 다이얼로그 | |
| You decide | Claude가 UX 흐름 판단 | |

**User's choice:** 마이크 전용 모드

## 시스템 오디오 품질

| Option | Description | Selected |
|--------|-------------|----------|
| 자동 정규화 | 두 소스의 RMS 레벨을 맞춤 | |
| 사용자 조절 | UI에 마이크/시스템 볼륨 슬라이더 제공 | |
| You decide | Claude가 기술적으로 판단 | ✓ |

**User's choice:** You decide

## 녹음 상태 표시

| Option | Description | Selected |
|--------|-------------|----------|
| 듀얼 레벨 미터 | 마이크/시스템 각각 작은 레벨 미터 표시 | |
| 단일 미터 + 배지 | 기존 레벨 미터 + 시스템 오디오 활성 배지 | |
| You decide | Claude가 UI 판단 | ✓ |

**User's choice:** You decide

## 에러 처리

| Option | Description | Selected |
|--------|-------------|----------|
| 마이크 계속 + 알림 | 시스템 오디오 실패해도 마이크 녹음 계속, 상태바 경고 | ✓ |
| 녹음 중지 | 시스템 오디오 실패 시 전체 녹음 중지 | |
| You decide | Claude가 판단 | |

**User's choice:** 마이크 계속 + 알림

## Claude's Discretion

- 볼륨 밸런싱/정규화 전략
- 녹음 상태 시각적 표시 디자인

## Deferred Ideas

None — discussion stayed within phase scope
