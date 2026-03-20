Done
- Polar checkout 생성 시 `customer_billing_address.country=KR`, `require_billing_address=true` preset 구현 완료
- checkout 진단 스크립트 `02_main/scripts/polar_checkout_inspect.py` 추가 완료
- Polar 운영 런북에 checkout 진단/`South Korea` preset 확인 절차 반영 완료
- 회귀 테스트 추가 및 `test_billing.py`, `test_polar_checkout_inspect.py` 통과 완료

In Progress
- 최우선 과제: Cloud Run 재배포 후 production checkout 진단과 실결제 1건 검증
- 진행 상태: 코드/문서/테스트는 완료됐고 운영 배포 및 실제 `checkout_id` 진단 실행은 미진행
- 다음 단계: backend 재배포 후 `py scripts/polar_checkout_inspect.py --checkout-id <CHECKOUT_ID>`로 preset/processor 상태를 확인하고 실결제 1건에서 `credits_applied=true`를 검증

Next
- Polar 운영 공통 실패 checkout 1건에 대해 진단 스크립트 재조회 결과 수집
- 실결제 후 `payment_events`, `credit_ledger`, `profiles.credits_balance` 적립 확인
- Nano Banana 운영 실데이터 1건 검증

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\billing.py`
- `D:\03_PROJECT\05_mathOCR\02_main\scripts\polar_checkout_inspect.py`
- `D:\03_PROJECT\05_mathOCR\02_main\docs\polar_production_runbook_ko.md`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_billing.py`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_polar_checkout_inspect.py`

Last State
- `cd D:\03_PROJECT\05_mathOCR && py -3.14 -m pytest 02_main\tests\test_billing.py 02_main\tests\test_polar_checkout_inspect.py` -> `44 passed`
- `cd D:\03_PROJECT\05_mathOCR && py -3.14 02_main\scripts\polar_checkout_inspect.py --help` -> success
- 작업트리에는 이번 작업 외 선행 변경이 유지됨: 루트 `.hwpx` 삭제/`templates/` 이동 변경
