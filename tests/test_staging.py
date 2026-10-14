import os
import time

from PIL import Image

from app.core.converter_registry import convert_file
from app.core.job import Job
from app.utils.files import unique_path
from app.utils.paths import new_job_dir, purge_stale_staging, staging_dir


def test_same_named_sources_do_not_overwrite_each_other(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(tmp_path / "a" / "foto.png")
    Image.new("RGB", (20, 20), (0, 255, 0)).save(tmp_path / "b" / "foto.png")

    results = []
    for sub in ("a", "b"):
        job = Job(src=tmp_path / sub / "foto.png", target_ext="jpg")
        dst = job.output_path(new_job_dir())
        job.dst = dst
        job.outputs = convert_file(job.src, dst)
        results.append(job)

    assert results[0].dst != results[1].dst
    assert Image.open(results[0].dst).size == (10, 10)
    assert Image.open(results[1].dst).size == (20, 20)


def test_job_cleanup_removes_staged_output(tmp_path):
    work = new_job_dir()
    out = work / "x.png"
    out.write_bytes(b"x")
    job = Job(src=tmp_path / "x.jpg", target_ext="png", work_dir=work, dst=out, outputs=[out])
    job.cleanup()
    assert not work.exists()
    assert job.dst is None and job.outputs == [] and job.work_dir is None
    job.cleanup()  # idempotent


def test_unique_path(tmp_path):
    p = tmp_path / "foto.jpg"
    assert unique_path(p) == p
    p.write_bytes(b"1")
    assert unique_path(p) == tmp_path / "foto (2).jpg"
    (tmp_path / "foto (2).jpg").write_bytes(b"2")
    assert unique_path(p) == tmp_path / "foto (3).jpg"


def test_purge_stale_staging_only_removes_old_entries():
    old, fresh = new_job_dir(), new_job_dir()
    (old / "f.txt").write_text("x")
    two_days_ago = time.time() - 48 * 3600
    os.utime(old, (two_days_ago, two_days_ago))
    purge_stale_staging()
    assert not old.exists()
    assert fresh.exists()
    assert staging_dir().exists()
