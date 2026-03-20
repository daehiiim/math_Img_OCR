Done
- HWPX export를 `math_templete_example.hwpx` 기준 템플릿으로 전환 완료
- masterpage/footer current-page-only 적용 및 exporter/template/style ref 검증 추가 완료
- `py -3 -m pytest 02_main\tests\test_exporter.py 02_main\tests\test_pipeline_storage.py -q` -> `20 passed`

In Progress
- 최우선 과제: Cloud Run 재배포 후 production checkout 진단과 실결제 1건 검증
- 진행 상태: Polar checkout 코드/문서/테스트는 완료됐고 운영 배포 및 실제 `checkout_id` 진단 실행은 미진행
- 다음 단계: backend 재배포 후 `py scripts/polar_checkout_inspect.py --checkout-id <CHECKOUT_ID>` 실행, 실결제 1건에서 `credits_applied=true` 검증

Next
- Polar 운영 공통 실패 checkout 1건 재조회 결과 수집
- 실결제 후 `payment_events`, `credit_ledger`, `profiles.credits_balance` 적립 확인
- HWPX 생성물 한글 수동 오픈 검증 1회 수행

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\vendor\hwpxskill-math\templates\base\`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\scripts\polar_checkout_inspect.py`

Last State
- 브랜치: `codex-hwpx-template-hardening`
- HWPX runtime required files에 `masterpage0.xml`, `masterpage1.xml`, `BinData/image1.PNG` 추가됨
- footer는 `numType="PAGE"`만 유지하고 정적 총페이지 텍스트 제거됨
- 작업트리에는 이번 HWPX 템플릿 자산 교체와 exporter/test 변경이 남아 있음
