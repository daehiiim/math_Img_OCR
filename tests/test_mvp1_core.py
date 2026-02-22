from app import core


def test_core_flow_works_without_fastapi():
    job = core.create_job_from_bytes("sample.png", b"img-bytes")
    job_id = job["job_id"]

    core.save_regions(
        job_id,
        [
            {
                "id": "q1",
                "polygon": [[1, 1], [100, 1], [100, 100], [1, 100]],
                "type": "mixed",
                "order": 1,
            }
        ],
    )
    core.run_pipeline(job_id)
    exported = core.export_hwpx(job_id)

    assert exported["download_url"].endswith(".hwpx")
    assert (core.ROOT / exported["download_url"]).exists()


def test_core_run_requires_regions():
    job = core.create_job_from_bytes("sample2.png", b"img-bytes")
    try:
        core.run_pipeline(job["job_id"])
        assert False, "expected ValueError"
    except ValueError:
        pass
