# 히어로 비디오 15초 루프 자산 재인코딩 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 공개 홈 히어로 배경 비디오를 밝은 구간 없는 15초 루프 자산으로 교체한다.

**Architecture:** 원본 비디오 분석과 자산 생성은 별도 Python 스크립트로 처리하고, 프런트는 새 자산 참조와 단순 `loop` 계약만 유지한다. 자산 생성은 자연스럽게 이어지는 원본 프레임 구간을 찾아 반복 배치하는 방식으로 구현하고, 광류 보간은 사용하지 않는다.

**Tech Stack:** Python, OpenCV, FFmpeg, React, TypeScript, Vitest, Vite

---

### Task 1: 도구와 계약을 먼저 고정

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.test.tsx`
- Create: `D:\03_PROJECT\05_mathOCR\docs\plans\2026-03-23-home-hero-video-15s-loop-design.md`
- Create: `D:\03_PROJECT\05_mathOCR\docs\plans\2026-03-23-home-hero-video-15s-loop-plan.md`

**Step 1: Write the failing test**

- 비디오가 기본 `loop=true` 를 유지하는지 검증한다.
- `loadedmetadata` 후 `playbackRate` 가 기본값 `1` 인지 검증한다.
- 수동 `timeupdate` 리셋이 제거된 계약으로 기대값을 바꾼다.

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/app/components/PublicHomePage.test.tsx`

Expected: 기존 `playbackRate` 조정과 `timeupdate` 리셋 계약 때문에 실패

### Task 2: 자산 생성 스크립트 작성

**Files:**
- Create: `D:\03_PROJECT\05_mathOCR\04_design_renewal\scripts\build_hero_timelapse_loop.py`

**Step 3: Write the failing behavior check**

- 스크립트가 없으므로 실행 실패를 먼저 확인한다.

Run: `py -3 04_design_renewal\scripts\build_hero_timelapse_loop.py --help`

Expected: 파일 없음 또는 실행 불가

**Step 4: Write minimal implementation**

- 원본 [star-timelapse.mp4](/D:/03_PROJECT/05_mathOCR/04_new_design/star-timelapse.mp4) 를 읽는다.
- 어두운 구간 후보를 분석한다.
- 시작/끝 프레임 차이가 작은 자연 루프 구간을 찾는다.
- 해당 원본 프레임 구간 인덱스를 반복해 15초 시퀀스를 만든다.
- `ffmpeg` 를 호출해 [hero-timelapse.mp4](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/assets/home/hero-timelapse.mp4), [hero-timelapse.webm](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/assets/home/hero-timelapse.webm), [hero-timelapse-poster.jpg](/D:/03_PROJECT/05_mathOCR/04_design_renewal/src/assets/home/hero-timelapse-poster.jpg) 를 재생성한다.
- 예상 가능한 에러와 사용자 메시지를 한국어 상수로 분리한다.

**Step 5: Run script to verify it works**

Run: `py -3 04_design_renewal\scripts\build_hero_timelapse_loop.py`

Expected: 세 자산이 새로 생성되고, 생성 로그에 선택 구간과 출력 길이가 표시

### Task 3: 프런트 연결 최소화

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PublicHomePage.tsx`

**Step 6: Write minimal implementation**

- `playbackRate` 와 `timeupdate` 기반 수동 루프 제어를 제거한다.
- 기본 `loop` 와 새 자산 참조만 유지한다.
- 함수 주석은 한국어로 갱신한다.

**Step 7: Run targeted test to verify it passes**

Run: `npm run test:run -- src/app/components/PublicHomePage.test.tsx`

Expected: PASS

### Task 4: 자산 메타데이터와 번들 검증

**Files:**
- Modify: `D:\03_PROJECT\05_mathOCR\log.md`
- Modify if needed: `D:\03_PROJECT\05_mathOCR\handoff.md`

**Step 8: Verify generated assets**

Run: `py -3 -c "import cv2; import json; from pathlib import Path; paths=[Path(r'D:\\03_PROJECT\\05_mathOCR\\04_design_renewal\\src\\assets\\home\\hero-timelapse.mp4'), Path(r'D:\\03_PROJECT\\05_mathOCR\\04_design_renewal\\src\\assets\\home\\hero-timelapse.webm')]; out={};\nfor path in paths:\n cap=cv2.VideoCapture(str(path)); fps=cap.get(cv2.CAP_PROP_FPS); frames=cap.get(cv2.CAP_PROP_FRAME_COUNT); out[path.name]={'fps':fps,'frames':frames,'duration':frames/fps if fps else 0}; cap.release();\nprint(json.dumps(out, ensure_ascii=False, indent=2))"`

Expected: 두 자산 모두 약 15초 길이와 목표 FPS를 가짐

**Step 9: Run final verification**

Run: `npm run test:run -- src/app/components/PublicHomePage.test.tsx`
Run: `npm run build`

Expected: 둘 다 성공

**Step 10: Update project records**

- `log.md` 에 자산 재생성 근거, 출력 메타데이터, 검증 결과를 한국어로 기록한다.
- 향후 작업 방향이 바뀔 때만 `handoff.md` 를 덮어쓴다.
