# Development Learnings — Meeting Transcriber v1.0

## 2026-03-25 — UI 재구성 + 버그 수정

### [2026-03-25T16:00] Stop 버튼 레이스 컨디션

**문제**: `_on_level_changed()` 시그널 핸들러에서 `self._audio_worker = None`으로 참조를 지워버림. AudioCaptureWorker가 stop() 후 마지막 level_changed를 emit할 때 `_on_capture_stopped()`보다 먼저 도착하여 worker 참조가 사라짐.

**교훈**: Qt 시그널은 비동기적으로 도착한다. 스레드 종료 시 시그널 순서를 보장할 수 없으므로, 리소스 정리는 반드시 lifecycle 시그널(`capture_stopped`) 핸들러에서만 수행해야 한다. level_changed 같은 빈번한 시그널 핸들러에서 상태를 변경하면 안 된다.

**수정**: `_on_level_changed()`는 순수하게 UI 업데이트만 수행. 녹음 데이터 수집과 worker 정리는 `_on_capture_stopped()`에서만.

### [2026-03-25T16:10] macOS 메뉴바 "python" 표시

**문제**: `QApplication`에 `setApplicationName()` 호출이 없어서 macOS 메뉴바에 실행 파일 이름("python")이 표시됨. 또한 앱 메뉴(File, View 등)가 전혀 없음.

**교훈**: macOS에서 PyQt6 앱은 반드시 `app.setApplicationName()`과 `app.setApplicationDisplayName()`을 호출해야 한다. 메뉴바는 `window.menuBar().addMenu()`로 추가. py2app 패키징 시 `NSApplicationName` plist 키도 필요.

**수정**: app.py에 applicationName 설정 + File/View 메뉴 추가. setup.py에 NSApplicationName 추가.

### [2026-03-25T16:20] 폰트 "-apple-system" 경고

**문제**: `QFont("-apple-system", ...)` 사용 시 Qt가 67ms 동안 폰트 별칭을 탐색하며 경고 출력: "Populating font family aliases took 67 ms."

**교훈**: PyQt6에서 macOS 시스템 폰트를 사용하려면 CSS 값(`-apple-system`)이 아닌 Qt 내부 이름(`.AppleSystemUIFont`)을 사용해야 한다. CSS 폰트 이름은 QSS에서만 유효하고, `QFont()` 생성자에서는 Qt 폰트 이름을 써야 한다.

**수정**: 모든 `QFont("-apple-system", ...)` → `QFont(".AppleSystemUIFont", ...)`

### [2026-03-25T16:30] Apple Voice Memos 스타일 UI 재구성

**피드백**: 기존 UI가 개발자 도구처럼 보임. Apple Voice Memos처럼 깔끔한 녹음 중심 UX 필요.

**변경사항**:
- QTreeView 폴더 트리 → QListWidget 녹음 리스트 (제목, 날짜, 길이)
- 상단 툴바 녹음 버튼 → 하단 원형 녹음 버튼 (64px, 빨간 원/사각형 토글)
- 레벨 바를 하단 컨트롤 바에 얇게 (4px) 배치
- "Tap to Record" / "Recording..." / "Processing..." 상태 텍스트
- 사이드바에 "Recordings" 헤더

**교훈**: 개발자가 보기에 기능적으로 완성되어도, 실제 사용자 UX 관점에서는 레이아웃과 시각적 계층이 중요하다. 녹음 앱에서 녹음 버튼은 가장 눈에 띄어야 하고, 사이드바는 결과물(녹음 리스트)을 보여줘야 한다.

### [2026-03-25T16:40] LSUIElement = True 문제

**문제**: setup.py에서 `LSUIElement: True`로 설정하면 앱이 Dock에 표시되지 않고, macOS 메뉴바도 비활성화됨.

**교훈**: LSUIElement는 순수 메뉴바 상주 앱(e.g. Bartender, Alfred)에만 사용. 메인 윈도우가 있는 앱은 False로 설정해야 메뉴바와 Dock이 정상 동작.

**수정**: `LSUIElement: False`

### [2026-03-25T17:00] whisper-cli `-oj` 플래그 오해

**문제**: `-oj` (output-json) 플래그가 JSON을 stdout으로 출력한다고 가정했지만, 실제로는 JSON **파일**을 생성한다. stdout에는 VTT 형식이 출력됨. `-of OUTPUT_PATH` 플래그로 출력 파일 경로를 지정해야 `OUTPUT_PATH.json` 파일이 생성된다.

**교훈**: 외부 CLI 도구의 플래그는 반드시 실제 실행하여 확인해야 한다. `--help` 설명("output result in a JSON file")이 "JSON을 stdout에 출력"이 아니라 "JSON 파일을 생성"이라는 의미였다. 단위 테스트에서 subprocess를 mock하면 이런 실제 동작 차이를 발견할 수 없다.

**수정**: `transcriber.py`에서 `-of TEMP_PATH` 추가. subprocess 실행 후 `TEMP_PATH.json` 파일을 읽고 삭제.

### [2026-03-25T17:10] E2E 파이프라인 검증 성공

녹음(3초) → WAV 인코딩 → whisper-cli 전사 → 세그먼트 파싱 전체 흐름 확인.
- AudioCaptureWorker: 2초 청크 1개 + silence 1개 정상 동작
- encode_wav_chunk: 64KB WAV 생성
- FileTranscriber: whisper-small 모델로 "auto" 언어 감지 → 1 segment 반환
- 전체 소요 시간: ~5초 (3초 녹음 + ~2초 전사)

### [2026-03-25T17:30] GUI 전체 파이프라인 E2E 검증 성공

GUI(MainWindow) 경유 전체 흐름 확인:
- RecordButton 클릭 → AudioCaptureWorker.start() → 3초 녹음
- 정지 → _on_capture_stopped → encode_wav_chunk → temp WAV
- TranscriptionWorkerThread(QThread) → FileTranscriber.transcribe_file()
- whisper-cli -oj -of 실행 → JSON 파일 파싱 → 1 segment
- create_transcript → save_transcript → ~/.meeting_transcriber/Work/ 저장
- _refresh_recording_list → 사이드바 갱신
- status_bar: "Saved: 2026-03-25_142112"

**추가 방어 코드**: 빈 JSON 파일 체크, 상세 에러 메시지 (stderr 포함)로 향후 디버깅 용이.

## 2026-03-26 — v1.5 AI 통합 + UI 개선

### [2026-03-26T00:00] P9: Gemini AI Provider 구현

- `ai/provider_base.py`: ABC 5개 메서드 (summarize, proofread, translate, extract_keywords, generate_title)
- `ai/gemini_provider.py`: Gemini 2.0 Flash 구현, Keychain에서 API 키 로드
- `ai/tasks.py`: AITaskWorker(QThread) — 순차 실행 (교열→요약→키워드→제목)
- MainWindow._run_ai_tasks(): 전사 완료 후 API 키 있으면 자동 실행

### [2026-03-26T00:10] P10: Spotlight 스타일 오버레이

- 화면 하단 중앙 고정 (600x80), 둥근 필 바
- 녹음 중 빨간 점 표시 (set_recording)
- toggle_visibility() 시 center_on_screen() 자동 호출

### [2026-03-26T00:20] Socratic Review (5 에이전트)

발견 이슈:
- CRITICAL: 청크 워커 스레드 무한 생성 → 최대 2개 제한 + 완료 워커 자동 정리
- HIGH: _is_recording 비공개 접근 → is_recording property 추가
- HIGH: AI 모듈 dead code → MainWindow에 연결 완료

### [2026-03-26T00:30] P11: TranscriptViewer 3탭

- Tab 0 (Original): 원본 세그먼트 텍스트
- Tab 1 (Proofread): AI 교열 결과 (편집 가능 + Save 버튼)
- Tab 2 (Summary): AI 요약 + 키워드 태그
- exporter.py: include_ai_results 파라미터 추가 (Markdown/TXT)
