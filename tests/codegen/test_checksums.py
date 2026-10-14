from codegen import checksums


def test_record_and_verify(tmp_path):
    versions = tmp_path / "migrations" / "versions"
    versions.mkdir(parents=True)
    f = versions / "001_init.py"
    f.write_text("x = 1\n")
    checksums.record(tmp_path, f)
    assert checksums.verify(tmp_path) == []
    f.write_text("x = 2\n")
    assert any("001_init.py" in e for e in checksums.verify(tmp_path))
    (versions / "002_new.py").write_text("y = 1\n")
    assert any("002_new.py" in e and "未登録" in e for e in checksums.verify(tmp_path))
