"""`hersona update` (hersona.core.update) の回帰テスト。

ネットワークは fake opener (in-memory tar.gz) で差し替え、実際の HTTP は行わない。
データキャッシュ先は HERSONA_DATA_DIR を tmp に向けて隔離する。
"""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
import urllib.error
import urllib.request

import pytest

from hersona.cli.app import main
from hersona.core import paths, update


def _make_archive(files: dict[str, str], *, top: str = "hersona-main") -> bytes:
    """GitHub アーカイブ相当の tar.gz バイト列を作る。

    ``files`` は「先頭ディレクトリを除いた相対パス -> 中身」。全エントリは
    ``<top>/`` 配下に入る (GitHub の codeload 仕様)。
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=f"{top}/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _opener_for(archive: bytes):
    """fake urlopen: Request を受けて archive を返す callable。"""

    def _open(_request):
        return io.BytesIO(archive)

    return _open


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_DATA_DIR", str(tmp_path / "data"))


def test_archive_url_uses_codeload() -> None:
    assert (
        update.archive_url("v1.4.1")
        == "https://codeload.github.com/shiro-0x/hersona/tar.gz/v1.4.1"
    )
    assert update.archive_url() == "https://codeload.github.com/shiro-0x/hersona/tar.gz/main"


def test_update_data_installs_attributes_and_schema() -> None:
    archive = _make_archive(
        {
            "attributes/personality/sample.yaml": "attribute_name: sample\n",
            "attributes/speech/other.yaml": "attribute_name: other\n",
            "schema/attribute.schema.json": "{}\n",
            "README.md": "ignored top-level file\n",
        }
    )
    result = update.update_data(opener=_opener_for(archive))

    assert result.attribute_files == 2
    assert result.schema_files == 1
    assert sorted(result.updated_dirs) == ["attributes", "schema"]

    dest = paths.data_cache_root()
    assert (dest / "attributes" / "personality" / "sample.yaml").is_file()
    assert (dest / "schema" / "attribute.schema.json").is_file()
    # data ディレクトリ外のトップレベルファイルは展開しない
    assert not (dest / "README.md").exists()


def test_update_takes_precedence_in_paths() -> None:
    archive = _make_archive({"attributes/personality/sample.yaml": "attribute_name: sample\n"})
    update.update_data(opener=_opener_for(archive))

    # paths はキャッシュを同梱データより優先して解決する
    resolved = paths.public_attributes_root()
    assert resolved == paths.data_cache_root() / "attributes"


def test_update_is_atomic_replace() -> None:
    first = _make_archive(
        {
            "attributes/personality/a.yaml": "attribute_name: a\n",
            "attributes/personality/b.yaml": "attribute_name: b\n",
        }
    )
    update.update_data(opener=_opener_for(first))
    # 2 回目は 1 件のみ。古いファイルが残らず置き換わること。
    second = _make_archive({"attributes/personality/a.yaml": "attribute_name: a\n"})
    result = update.update_data(opener=_opener_for(second))

    dest = paths.data_cache_root()
    assert result.attribute_files == 1
    assert (dest / "attributes" / "personality" / "a.yaml").is_file()
    assert not (dest / "attributes" / "personality" / "b.yaml").exists()


def test_update_rejects_archive_without_data_dirs() -> None:
    archive = _make_archive({"README.md": "no data dirs here\n"})
    with pytest.raises(update.UpdateError):
        update.update_data(opener=_opener_for(archive))


def test_update_ignores_path_traversal_members() -> None:
    # 先頭ディレクトリを外すと "../evil.yaml" になるエントリは無視する。
    archive = _make_archive(
        {
            "attributes/ok.yaml": "attribute_name: ok\n",
            "../evil.yaml": "attribute_name: evil\n",
        }
    )
    result = update.update_data(opener=_opener_for(archive))
    dest = paths.data_cache_root()
    assert (dest / "attributes" / "ok.yaml").is_file()
    assert not (dest.parent / "evil.yaml").exists()
    assert result.attribute_files == 1


def test_clear_data_cache_reverts() -> None:
    archive = _make_archive({"attributes/personality/sample.yaml": "attribute_name: sample\n"})
    update.update_data(opener=_opener_for(archive))
    dest = paths.data_cache_root()
    assert (dest / "attributes").exists()

    removed = update.clear_data_cache()
    assert removed == ["attributes"]
    assert not (dest / "attributes").exists()
    # キャッシュが無くなれば paths は同梱データへフォールバックする
    assert paths.public_attributes_root() != dest / "attributes"


def test_clear_data_cache_when_empty() -> None:
    assert update.clear_data_cache() == []


def test_cli_update_dry_run(capsys) -> None:
    assert main(["update", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "codeload.github.com/shiro-0x/hersona" in out
    # dry-run はネットワークもファイル書き込みもしない
    assert not paths.data_cache_root().exists()


def test_cli_update_clear_none(capsys) -> None:
    assert main(["update", "--clear"]) == 0
    out = capsys.readouterr().out
    assert "No downloaded data" in out


def test_cli_update_error_returns_1(capsys, monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise update.UpdateError("network down")

    monkeypatch.setattr("hersona.core.update.update_data", _boom)
    assert main(["update"]) == 1
    err = capsys.readouterr().err
    assert "network down" in err


# --- checksums.json 検証 (外部レビュー対応 §P2-1) --------------------------


def _dual_opener(archive: bytes, manifest_bytes: bytes | None):
    """codeload と raw.githubusercontent.com とで別々のレスポンスを返す fake opener。

    ``manifest_bytes=None`` なら raw.githubusercontent.com への到達は 404 扱い
    (manifest 未提供 = 検証スキップの再現)。
    """
    def _open(request):
        url = request.full_url
        if "raw.githubusercontent.com" in url:
            if manifest_bytes is None:
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            return io.BytesIO(manifest_bytes)
        return io.BytesIO(archive)

    return _open


def test_checksums_url_uses_raw_githubusercontent() -> None:
    assert (
        update.checksums_url("v1.4.1")
        == "https://raw.githubusercontent.com/shiro-0x/hersona/v1.4.1/checksums.json"
    )


def test_update_verifies_checksums_when_manifest_matches() -> None:
    files = {"attributes/personality/sample.yaml": "attribute_name: sample\n"}
    archive = _make_archive(files)
    manifest = {
        "algorithm": "sha256",
        "files": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()},
    }
    result = update.update_data(
        opener=_dual_opener(archive, json.dumps(manifest).encode())
    )
    assert result.checksum_verified is True
    assert result.attribute_files == 1


def test_update_raises_on_checksum_mismatch_and_does_not_install() -> None:
    files = {"attributes/personality/sample.yaml": "attribute_name: sample\n"}
    archive = _make_archive(files)
    manifest = {
        "algorithm": "sha256",
        "files": {"attributes/personality/sample.yaml": "0" * 64},
    }
    with pytest.raises(update.ChecksumMismatchError):
        update.update_data(opener=_dual_opener(archive, json.dumps(manifest).encode()))
    # 不一致時はインストールを中止する (キャッシュに反映されない)
    dest = paths.data_cache_root()
    assert not (dest / "attributes").exists()


def test_update_skips_verification_when_manifest_missing() -> None:
    archive = _make_archive({"attributes/personality/sample.yaml": "attribute_name: sample\n"})
    result = update.update_data(opener=_dual_opener(archive, None))
    assert result.checksum_verified is False
    assert result.attribute_files == 1  # manifest 無しでもインストールは続行 (fail-open)


def test_update_no_verify_flag_skips_checksum_fetch() -> None:
    files = {"attributes/personality/sample.yaml": "attribute_name: sample\n"}
    archive = _make_archive(files)
    # 不一致な manifest を用意しても --no-verify (verify_checksums=False) なら参照しない
    manifest = {"algorithm": "sha256", "files": {"attributes/personality/sample.yaml": "0" * 64}}
    result = update.update_data(
        opener=_dual_opener(archive, json.dumps(manifest).encode()),
        verify_checksums=False,
    )
    assert result.checksum_verified is False
    assert result.attribute_files == 1


def test_cli_update_reports_checksum_verified(capsys, monkeypatch) -> None:
    files = {"attributes/personality/sample.yaml": "attribute_name: sample\n"}
    archive = _make_archive(files)
    manifest = {
        "algorithm": "sha256",
        "files": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()},
    }
    fake_open = _dual_opener(archive, json.dumps(manifest).encode())
    # _cmd_update は opener を渡さず update_data() を呼ぶため、既定の
    # urllib.request.urlopen を差し替えて検証する (実ネットワークは行わない)。
    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    assert main(["update"]) == 0
    out = capsys.readouterr().out
    assert "verified" in out.lower() or "確認" in out
