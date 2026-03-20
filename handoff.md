Done
- HWPX export 기준 템플릿을 `result_answer.hwpx` 기반으로 재교체 완료
- `section0.xml` 합성형 exporter를 레퍼런스 블록 복제형 renderer로 교체 완료
- footer current-page-only 적용 완료
- `templates/generated_example.hwpx` 재생성 완료
- `py -3 -m pytest 02_main\tests\test_exporter.py 02_main\tests\test_pipeline_storage.py -q` -> `23 passed`

In Progress
- 최우선 과제: 한글에서 `generated_example.hwpx` 수동 오픈 검증
- 진행 상태: XML 구조/테스트 비교는 통과했고 `result_answer`와 header/first block/picture/choice 구조 일치 확인 완료
- 다음 단계: 한글에서 `generated_example.hwpx` 와 `result_answer.hwpx` 를 나란히 열어 시각 차이 확인

Next
- 수동 오픈에서 어긋나는 줄간격/탭/이미지 크기 있으면 `hwpx_reference_renderer.py` 미세 조정
- 실제 OCR job 데이터 1건으로 export 재검증

Related Files
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\exporter.py`
- `D:\03_PROJECT\05_mathOCR\02_main\app\pipeline\hwpx_reference_renderer.py`
- `D:\03_PROJECT\05_mathOCR\02_main\vendor\hwpxskill-math\templates\base\`
- `D:\03_PROJECT\05_mathOCR\02_main\tests\test_exporter.py`
- `D:\03_PROJECT\05_mathOCR\templates\generated_example.hwpx`

Last State
- 브랜치: `codex-hwpx-template-hardening`
- runtime required image는 `BinData/image1.bmp` 기준
- `generated_example.hwpx` 구조 비교: header `27/35/30`, 첫 문단 `29/1/tbl+line+rect`, 그림 `34/1`, 보기 `11/4`, footer 총페이지 제거
