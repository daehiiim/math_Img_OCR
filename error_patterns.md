# Error Patterns

- direct writer에서 problem/explanation 본문에 `<math>...</math>` markup이 들어오면 Text run에 그대로 넣지 않는다. run 생성 전에 반드시 segment로 분해해 Text/Equation run으로 재조립한다.
- equation width는 템플릿 샘플 폭을 순환 재사용하지 않는다. script 길이 샘플을 다시 계산해 문맥별 Equation run 폭을 매번 추정한다.
