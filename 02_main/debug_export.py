import sys
sys.path.append(r'D:\03_PROJECT\05_mathOCR\02_main')
from app.pipeline.orchestrator import execute_hwpx_export
import traceback

try:
    execute_hwpx_export('job_dd224e9b3143')
    print('SUCCESS')
except Exception as e:
    traceback.print_exc()
