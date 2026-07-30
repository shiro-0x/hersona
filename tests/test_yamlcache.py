"""`hersona.core.yamlcache` の mtime 無効化とキャッシュ汚染防止を検証。"""
from __future__ import annotations

import os

import pytest

from hersona.core import yamlcache
from hersona.core.attach import load_attribute


@pytest.fixture(autouse=True)
def _clear_cache():
    yamlcache.clear_cache()
    yield
    yamlcache.clear_cache()


def _write(path, text: str, *, mtime: float | None = None) -> None:
    path.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def test_returns_parsed_mapping(tmp_path):
    p = tmp_path / "a.yaml"
    _write(p, "attribute_name: x\nvalue: 1\n")
    assert yamlcache.load_yaml(p) == {"attribute_name": "x", "value": 1}


def test_second_read_is_served_from_cache(tmp_path):
    p = tmp_path / "a.yaml"
    _write(p, "value: 1\n")
    assert yamlcache.load_yaml(p) == {"value": 1}
    assert yamlcache.cache_size() == 1
    # 同じ mtime/size のままなら再パースせずキャッシュを返す。
    assert yamlcache.load_yaml(p) == {"value": 1}
    assert yamlcache.cache_size() == 1


def test_content_change_invalidates_cache(tmp_path):
    """同サイズでも mtime が動けば再パースされる (hersona update / テスト書き換え)。"""
    p = tmp_path / "a.yaml"
    _write(p, "value: 1\n", mtime=1_000_000)
    assert yamlcache.load_yaml(p) == {"value": 1}
    _write(p, "value: 2\n", mtime=2_000_000)
    assert yamlcache.load_yaml(p) == {"value": 2}


def test_size_change_invalidates_cache_even_at_same_mtime(tmp_path):
    """mtime を固定しても size が変われば無効化される (粗い FS 分解能への保険)。"""
    p = tmp_path / "a.yaml"
    _write(p, "value: 1\n", mtime=1_000_000)
    assert yamlcache.load_yaml(p) == {"value": 1}
    _write(p, "value: 22222\n", mtime=1_000_000)
    assert yamlcache.load_yaml(p) == {"value": 22222}


def test_missing_file_returns_default_and_does_not_cache(tmp_path):
    p = tmp_path / "nope.yaml"
    assert yamlcache.load_yaml(p) is None
    assert yamlcache.load_yaml(p, default={}) == {}
    assert yamlcache.cache_size() == 0


def test_broken_yaml_returns_default(tmp_path):
    p = tmp_path / "bad.yaml"
    _write(p, "a: [1, 2\n  b: :\n")
    assert yamlcache.load_yaml(p, default={}) == {}


def test_empty_file_returns_default(tmp_path):
    p = tmp_path / "empty.yaml"
    _write(p, "")
    assert yamlcache.load_yaml(p, default={}) == {}


def test_copy_result_isolates_caller_mutation(tmp_path):
    """既定 (copy_result=True) では呼び出し側の変更がキャッシュへ漏れない。"""
    p = tmp_path / "a.yaml"
    _write(p, "outer:\n  inner: [1, 2]\n")
    first = yamlcache.load_yaml(p)
    first["outer"]["inner"].append(3)
    first["added"] = True
    second = yamlcache.load_yaml(p)
    assert second == {"outer": {"inner": [1, 2]}}


def test_copy_result_false_shares_the_cached_object(tmp_path):
    """読み取り専用経路は同一オブジェクトを返す (コピー費用を省くため)。"""
    p = tmp_path / "a.yaml"
    _write(p, "value: 1\n")
    a = yamlcache.load_yaml(p, copy_result=False)
    b = yamlcache.load_yaml(p, copy_result=False)
    assert a is b


def test_clear_cache_forces_reparse(tmp_path):
    p = tmp_path / "a.yaml"
    _write(p, "value: 1\n")
    yamlcache.load_yaml(p)
    assert yamlcache.cache_size() == 1
    yamlcache.clear_cache()
    assert yamlcache.cache_size() == 0
    assert yamlcache.load_yaml(p) == {"value": 1}


def test_loader_prefers_libyaml_when_available():
    """libyaml があれば CSafeLoader、無ければ SafeLoader にフォールバックする。"""
    assert yamlcache.LOADER_NAME in ("CSafeLoader", "SafeLoader")


def test_load_attribute_result_is_not_shared_with_the_cache():
    """公開 API の戻り値を変更してもカタログのキャッシュは汚染されない。"""
    first = load_attribute("tsundere")
    first["catchphrases"] = ["MUTATED"]
    first["attribute_category"] = "MUTATED"
    second = load_attribute("tsundere")
    assert second["attribute_category"] == "personality"
    assert second["catchphrases"] != ["MUTATED"]


def test_user_namespace_override_still_wins_after_caching(tmp_path):
    """キャッシュ導入後も user 名前空間が公開属性を上書きする。"""
    user_root = tmp_path / "user"
    (user_root / "personality").mkdir(parents=True)
    _write(
        user_root / "personality" / "tsundere.yaml",
        "attribute_name: tsundere\n"
        "attribute_category: personality\n"
        "display_name: Overridden\n",
    )
    got = load_attribute("tsundere", user_root=user_root)
    assert got["display_name"] == "Overridden"
