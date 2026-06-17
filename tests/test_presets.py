"""ブレンドプリセット (hersona.core.presets) の回帰テスト (ROADMAP C: save)。

- save_preset が YAML を書き、load_preset で往復できる
- snake_case 以外のプリセット名 / 空属性は PresetError
- 同名既存は overwrite=False で拒否、True で上書き
- list_presets は名前昇順、delete_preset は削除
- presets_root は HERSONA_PRESETS_DIR / 属性ルート兄弟を解決
"""
from __future__ import annotations

import pytest

from hersona.core.presets import (
    Preset,
    PresetError,
    delete_preset,
    list_presets,
    load_preset,
    presets_root,
    save_preset,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_PRESETS_DIR", str(tmp_path / "presets"))


def test_save_and_load_roundtrip() -> None:
    dest = save_preset("my_tsun", ["tsundere", "keigo"], weight="strong", note="hi")
    assert dest.exists()
    assert dest.name == "my_tsun.yaml"

    p = load_preset("my_tsun")
    assert p.name == "my_tsun"
    assert p.attributes == ["tsundere", "keigo"]
    assert p.weight == "strong"
    assert p.note == "hi"
    assert p.created  # ISO date set on save


def test_save_default_weight_is_moderate() -> None:
    save_preset("plain", ["genki"])
    assert load_preset("plain").weight == "moderate"


def test_save_rejects_bad_name() -> None:
    for bad in ["Bad-Name", "9leading", "has space", "", "UPPER"]:
        with pytest.raises(PresetError):
            save_preset(bad, ["tsundere"])


def test_save_rejects_empty_attributes() -> None:
    with pytest.raises(PresetError):
        save_preset("empty", [])


def test_save_no_overwrite_then_overwrite() -> None:
    save_preset("dup", ["tsundere"])
    with pytest.raises(PresetError):
        save_preset("dup", ["genki"])
    # overwrite=True succeeds and replaces content
    save_preset("dup", ["genki"], overwrite=True)
    assert load_preset("dup").attributes == ["genki"]


def test_load_missing_raises() -> None:
    with pytest.raises(PresetError):
        load_preset("nope")


def test_list_presets_sorted() -> None:
    save_preset("zeta", ["genki"])
    save_preset("alpha", ["tsundere"])
    names = [p.name for p in list_presets()]
    assert names == ["alpha", "zeta"]


def test_list_presets_empty_when_none() -> None:
    assert list_presets() == []


def test_delete_preset() -> None:
    save_preset("temp", ["genki"])
    removed = delete_preset("temp")
    assert not removed.exists()
    assert list_presets() == []
    with pytest.raises(PresetError):
        delete_preset("temp")


def test_presets_root_uses_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HERSONA_PRESETS_DIR", str(tmp_path / "custom"))
    assert presets_root() == tmp_path / "custom"


def test_presets_root_defaults_to_user_root_sibling(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HERSONA_PRESETS_DIR", raising=False)
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "attrs"))
    assert presets_root() == tmp_path / "presets"


def test_preset_from_dict_rejects_non_dict() -> None:
    with pytest.raises(PresetError):
        Preset.from_dict(["not", "a", "dict"])  # type: ignore[arg-type]


def test_preset_from_dict_rejects_bad_attributes() -> None:
    with pytest.raises(PresetError):
        Preset.from_dict({"preset_name": "x", "attributes": "tsundere"})


def test_list_skips_malformed_yaml() -> None:
    root = presets_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "broken.yaml").write_text("preset_name: x\nattributes: not_a_list\n", encoding="utf-8")
    save_preset("good", ["genki"])
    # malformed entry is skipped, valid one remains
    names = [p.name for p in list_presets()]
    assert names == ["good"]


def test_load_fills_name_from_filename() -> None:
    root = presets_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "noname.yaml").write_text("attributes:\n- genki\nweight: mild\n", encoding="utf-8")
    p = load_preset("noname")
    assert p.name == "noname"
    assert p.attributes == ["genki"]
    assert p.weight == "mild"


def test_preset_roundtrip_with_intensity_baseline() -> None:
    from hersona.core.intensity import IntensityReport

    baseline = IntensityReport(
        score=78.0,
        endings_rate=0.8,
        catchphrase_hits=2,
        sentence_count=3,
        band=(70, 100),
        status="pass",
        lang="ja",
    )
    save_preset("with_baseline", ["keigo"], intensity_baseline=baseline)
    p = load_preset("with_baseline")
    assert p.intensity_baseline == {
        "score": 78.0,
        "endings_rate": 0.8,
        "catchphrase_hits": 2,
        "sentence_count": 3,
        "band": [70, 100],
        "status": "pass",
        "lang": "ja",
        "first_person_hits": 0,
    }


def test_preset_from_dict_omits_missing_baseline_gracefully() -> None:
    p = Preset.from_dict({"preset_name": "legacy", "attributes": ["tsundere"]})
    assert p.intensity_baseline is None
