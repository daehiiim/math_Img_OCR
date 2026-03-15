from __future__ import annotations

import json

from app import core


def main() -> None:
    job = core.create_job_from_bytes("demo.png", b"demo-image")
    job_id = job["job_id"]

    core.save_regions(
        job_id,
        [
            {
                "id": "q1",
                "polygon": [[10, 10], [220, 10], [220, 140], [10, 140]],
                "type": "mixed",
                "order": 1,
            }
        ],
    )
    core.run_pipeline(job_id)
    export_info = core.export_hwpx(job_id)
    final = core.read_job(job_id)

    print(json.dumps({"job_id": job_id, "export": export_info, "status": final["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
