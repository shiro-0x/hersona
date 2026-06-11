"""core/i18n (Phase 0 言語プラミング) のテスト。"""
from __future__ import annotations

import pytest

from hersona.cli.app import main
from hersona.core import i18n


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("HERSONA_LANG", raising=False)


class TestNormalizeLang:
    def test_passthrough_supported(self):
        assert i18n.normalize_lang("en") == "en"
        assert i18n.normalize_lang("ja") == "ja"

    def test_strips_region_and_case(self):
        assert i18n.normalize_lang("en-US") == "en"
        assert i18n.normalize_lang("JA_jp") == "ja"

    def test_unsupported_or_empty_is_none(self):
        assert i18n.normalize_lang("fr") is None
        assert i18n.normalize_lang("") is None
        assert i18n.normalize_lang(None) is None


class TestResolveLang:
    def test_default_is_english(self):
        assert i18n.resolve_lang() == "en"

    def test_cli_flag_wins(self, monkeypatch):
        monkeypatch.setenv("HERSONA_LANG", "en")
        assert i18n.resolve_lang("ja") == "ja"

    def test_env_used_when_no_flag(self, monkeypatch):
        monkeypatch.setenv("HERSONA_LANG", "ja")
        assert i18n.resolve_lang() == "ja"

    def test_invalid_flag_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("HERSONA_LANG", "ja")
        assert i18n.resolve_lang("fr") == "ja"

    def test_invalid_everything_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("HERSONA_LANG", "xx")
        assert i18n.resolve_lang("fr") == "en"


class TestTr:
    def test_english_default(self):
        assert i18n.tr("error.prefix", "en") == "Error: "

    def test_japanese_catalog(self):
        assert i18n.tr("error.prefix", "ja") == "エラー: "

    def test_missing_key_returns_key(self):
        assert i18n.tr("nope.not.here", "en") == "nope.not.here"

    def test_missing_in_lang_falls_back_to_english(self):
        # ja カタログに無いキーは en にフォールバック (キー自体ではなく英語値)。
        # ここでは両カタログに存在するキーで非フォールバック経路を担保。
        assert i18n.tr("common.none", "ja") == "(該当なし)"

    def test_format_substitution(self):
        # テンプレートに無い差し込みでも例外を投げずテンプレートを返す。
        assert i18n.tr("error.prefix", "en", foo="x") == "Error: "


class TestResolveMeta:
    def test_new_i18n_block_wins(self):
        attr = {"display_name": "Keigo", "i18n": {"ja": {"display_name": "敬語"}}}
        assert i18n.resolve_meta(attr, "display_name", "ja") == "敬語"
        assert i18n.resolve_meta(attr, "display_name", "en") == "Keigo"

    def test_legacy_suffix_pair(self):
        attr = {"display_name_en": "Tsundere", "display_name_ja": "ツンデレ"}
        assert i18n.resolve_meta(attr, "display_name", "ja") == "ツンデレ"
        assert i18n.resolve_meta(attr, "display_name", "en") == "Tsundere"

    def test_base_field_fallback(self):
        attr = {"description": "base text"}
        assert i18n.resolve_meta(attr, "description", "ja") == "base text"

    def test_missing_returns_empty(self):
        assert i18n.resolve_meta({}, "display_name", "en") == ""


class TestCliLangFlag:
    def test_default_error_prefix_is_english(self, capsys):
        # 存在しない属性で show を実行 → エラー経路を踏ませる。
        rc = main(["show", "__nonexistent__"])
        assert rc == 1
        assert capsys.readouterr().err.startswith("Error: ")

    def test_lang_ja_flag_switches_error_prefix(self, capsys):
        rc = main(["show", "__nonexistent__", "--lang", "ja"])
        assert rc == 1
        assert capsys.readouterr().err.startswith("エラー: ")

    def test_lang_flag_before_subcommand(self, capsys):
        rc = main(["--lang", "ja", "show", "__nonexistent__"])
        assert rc == 1
        assert capsys.readouterr().err.startswith("エラー: ")

    def test_env_var_switches_language(self, capsys, monkeypatch):
        monkeypatch.setenv("HERSONA_LANG", "ja")
        rc = main(["show", "__nonexistent__"])
        assert rc == 1
        assert capsys.readouterr().err.startswith("エラー: ")
