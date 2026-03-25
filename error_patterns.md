# Error Patterns

- direct writer에서 problem/explanation 본문에 `<math>...</math>` markup이 들어오면 Text run에 그대로 넣지 않는다. run 생성 전에 반드시 segment로 분해해 Text/Equation run으로 재조립한다.
- equation width는 템플릿 샘플 폭을 순환 재사용하지 않는다. script 길이 샘플을 다시 계산해 문맥별 Equation run 폭을 매번 추정한다.
- direct HwpForge 결과의 inline mixed 문단은 여러 `hp:run`으로 남기지 않는다. `text/equation`만 있는 문단은 export 직후 한 run으로 합치고 compact width 프로파일까지 함께 보정한다.
- 해설 mixed 문단의 inline equation은 `width`만 보정하지 않는다. 한글 정상 저장본과 같은 compact box profile(`height=975`, `baseLine=86`)을 함께 맞춘다.
- compact inline width lookup은 raw script 문자열 그대로 비교하지 않는다. `ANGLE`/`∠`, 공백 차이를 제거한 canonical key로 answer 샘플과 reference 폭을 매칭한다.
- 해설 mixed 문단에서 같은 script가 문맥마다 다른 equation box로 저장되면 실패로 본다. 특히 짧은 산술식이 `width=8386`, `height=1125`, `baseLine=85` 로 남아 있으면 export 전에 `script별 width + height=975 + baseLine=86` 규칙으로 다시 보정한다.
- OCR 원문은 `ordered_segments`와 `raw_transcript`를 함께 저장하고, plain text는 재작성하지 않는다. 정규화는 `math` segment와 export 파생 필드에만 제한한다.
- 객관식 해설은 자유문장만 저장하지 않는다. 구조화된 정답 번호/값을 선택지와 대조해 불일치 시 해설 원문 대신 검증 경고 문구로 대체한다.
- Pydantic 모델에 `TypedDict`를 넣을 때 Cloud Run Python 3.10 런타임을 유지한다면 `typing.TypedDict`를 쓰지 않는다. 반드시 `typing_extensions.TypedDict`를 사용하고 호환 분기 schema 재구성 테스트로 확인한다.
- 짧은 원본 타임랩스를 긴 루프로 늘릴 때 광류 보간으로 대부분 프레임을 합성하지 않는다. 합성 프레임 비율이 높아지면 잔상과 버벅임이 생기므로, 먼저 자연스럽게 이어지는 원본 프레임 루프 구간을 찾고 그 구간 반복을 우선 검토한다.
- 배경 비디오에 별도 poster 레이어를 둘 때는 `loadeddata` 이후 즉시 제거한다. 재생 중에도 정지 poster가 남아 있으면 움직이는 프레임 위에 고정 별 위치가 겹쳐 잔상처럼 보인다.
