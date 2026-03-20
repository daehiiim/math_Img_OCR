Done
- Polar production 상품 3개 metadata(`plan_id`, `credits`) 복구 완료
- 운영 `/billing/catalog` 200 복구 및 `/pricing` 구매 버튼 노출 확인 완료
- live `/billing/checkout` 세션 생성 검증 및 `02_main/.env` Polar 값 운영 기준 동기화 완료
- 프런트 fallback/local mock/test 카탈로그 가격을 live 기준(`100/9900/19000 KRW`)으로 정렬 완료

In Progress
- 최우선 과제: Polar 운영 실결제 1건과 webhook 적립 최종 검증
- 진행 상태: catalog와 checkout 생성은 복구됐고 실제 카드 승인과 `credits_applied=true` 검증은 비용 발생 가능성 때문에 미실행
- 다음 단계: 사용자 승인 후 production 결제 1건을 수행하고 `GET /billing/checkout/{id}`, `payment_events`, `credit_ledger`, `profiles.credits_balance`를 확인

Next
- Nano Banana 운영 실데이터 1건 검증
- Polar 운영 가격 정책과 product display name(`single/starter/pro`) 정리 여부 결정
- Cloud Run 민감정보를 Secret Manager 참조로 이관 검토

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\billing.py`
- `D:\03_PROJECT\05_mathOCR\02_main\docs\polar_production_runbook_ko.md`
- `D:\03_PROJECT\05_mathOCR\02_main\.env`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\lib\billingCatalog.ts`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PricingPage.tsx`
- `D:\03_PROJECT\05_mathOCR\04_design_renewal\src\app\components\PaymentPage.tsx`

Last State
- `curl https://mathtohwp.vercel.app/billing/catalog` -> `200` with 3 plans
- `py scripts/polar_production_preflight.py --api-base-url https://mathocr-146126176673.us-central1.run.app` -> all `OK`
- authenticated `POST /billing/checkout` -> checkout 생성 성공, `GET /billing/checkout/{id}` -> `status=open`, `credits_applied=false`
- `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm test -- billingApi.test.ts PaymentPage.test.tsx PricingPage.test.tsx` -> `27 passed`
- `cd D:\03_PROJECT\05_mathOCR\04_design_renewal && npm run build` -> success
- 작업트리에는 이번 작업 외 선행 변경이 유지됨: `02_main/app/{billing,config,main}.py`, `02_main/app/pipeline/extractor.py`, `02_main/tests/{test_billing,test_config,test_nano_banana_prompt}.py`, `02_main/app/pipeline/prompt_assets/`
