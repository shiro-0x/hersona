"""hersona CLI (hersona.cli.app) の回帰テスト。

非対話フラグ経路を中心に main(argv) を直接呼んで stdout を検証する。
ユーザー名前空間は HERSONA_USER_DIR を tmp に向けて隔離する。
"""
from __future__ import annotations

import json

import pytest

from hersona.cli.app import main


@pytest.fixture(autouse=True)
def _isolate_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))


def test_list(capsys) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "Available attributes (177)" in out
    assert "tsundere" in out
    # 全カテゴリが見出しと属性ごと表示される (hobby / visual が抜け落ちない回帰防止)
    for cat in ("personality/", "speech/", "archetype/", "visual/", "hobby/"):
        assert cat in out
    assert "cooking" in out  # hobby
    assert "glasses" in out  # visual


def test_show(capsys) -> None:
    assert main(["show", "tsundere"]) == 0
    out = capsys.readouterr().out
    assert "personality/tsundere" in out
    assert "core_traits" in out


def test_show_with_category_prefix(capsys) -> None:
    assert main(["show", "personality/tsundere"]) == 0
    assert "personality/tsundere" in capsys.readouterr().out


def test_show_unknown_returns_error(capsys) -> None:
    assert main(["show", "nonexistent"]) == 1


def test_matrix_json(capsys) -> None:
    assert main(["matrix", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "attributes" in data
    assert "genki" in data["attributes"]


def test_blend(capsys) -> None:
    assert main(["blend", "tsundere", "keigo"]) == 0
    out = capsys.readouterr().out
    assert "tsundere" in out
    assert "core_traits" in out


def test_recommend_with_answers(capsys) -> None:
    assert main(["recommend", "--answers", "distance=1,speech=0,role=1"]) == 0
    out = capsys.readouterr().out
    assert "Recommendation" in out
    assert "tsundere" in out


def test_recommend_json(capsys) -> None:
    assert main(["recommend", "--answers", "distance=1", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "blend" in data
    assert "scores" in data


def test_recommend_apply_shows_block(capsys) -> None:
    assert main(["recommend", "--answers", "distance=1,speech=0", "--apply"]) == 0
    out = capsys.readouterr().out
    assert "injection block" in out


def test_recommend_en_lang_routes_to_english_speech(capsys) -> None:
    # W2: 表示言語 en (既定) では en クイズが使われ、英語 speech が推薦される。
    assert main(["recommend", "--answers", "speech=3,distance=1"]) == 0
    out = capsys.readouterr().out
    assert "southern_us_en" in out


def test_recommend_ja_lang_keeps_ja_quiz(capsys) -> None:
    # W2: --lang ja では従来の ja クイズのまま。英語 speech は推薦に出ない。
    assert main(["--lang", "ja", "recommend", "--answers", "speech=3,distance=1"]) == 0
    out = capsys.readouterr().out
    assert "_en" not in out


def test_create_and_roundtrip(capsys) -> None:
    rc = main(
        [
            "create",
            "--category", "personality",
            "--name", "cli_made",
            "--display-ja", "シーエルアイ",
            "--display-en", "CliMade",
            "--desc-ja", "せつめい",
            "--desc-en", "desc",
            "--example", "ex1",
        ]
    )
    assert rc == 0
    assert "Saved:" in capsys.readouterr().out
    # 直後に show で解決できる
    assert main(["show", "cli_made"]) == 0
    assert "personality/cli_made" in capsys.readouterr().out


def test_create_missing_required_flag_errors(capsys) -> None:
    rc = main(["create", "--category", "personality", "--name", "x"])
    assert rc == 1


def test_no_command_prints_help(capsys) -> None:
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_lang_ja_restores_japanese_output(capsys) -> None:
    # 既定 en に対し --lang ja で従来の日本語 UI に戻せること (A 層の往復)。
    assert main(["--lang", "ja", "list"]) == 0
    assert "177 件" in capsys.readouterr().out
    assert main(["recommend", "--answers", "distance=1,speech=0", "--lang", "ja"]) == 0
    assert "推薦結果" in capsys.readouterr().out


def test_lang_ja_localizes_core_error(capsys) -> None:
    # core 由来のエラーメッセージもロケールに追従すること。
    assert main(["--lang", "ja", "show", "nonexistent"]) == 1
    assert "属性が見つかりません" in capsys.readouterr().err
    assert main(["show", "nonexistent"]) == 1
    assert "attribute not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# preview コマンド (A1)
# ---------------------------------------------------------------------------

def test_preview_shows_inject_block_and_samples(capsys) -> None:
    assert main(["preview", "tsundere"]) == 0
    out = capsys.readouterr().out
    assert "preview: tsundere" in out
    assert "injection block" in out
    assert "core_traits" in out
    assert "sample phrases" in out


def test_preview_blend_multiple(capsys) -> None:
    assert main(["preview", "tsundere", "kyoto_ben", "--weight", "strong"]) == 0
    out = capsys.readouterr().out
    assert "tsundere + kyoto_ben" in out
    assert "strong" in out
    assert "sample phrases" in out
    # kyoto_ben has catchphrases → at least one bullet
    assert "•" in out


def test_preview_count_flag(capsys) -> None:
    assert main(["preview", "tsundere", "--count", "1"]) == 0
    out = capsys.readouterr().out
    bullets = [line for line in out.splitlines() if "•" in line]
    assert len(bullets) <= 1


def test_preview_category_prefix_accepted(capsys) -> None:
    assert main(["preview", "personality/tsundere"]) == 0
    assert "tsundere" in capsys.readouterr().out


def test_preview_ja_locale(capsys) -> None:
    assert main(["--lang", "ja", "preview", "tsundere"]) == 0
    out = capsys.readouterr().out
    assert "プレビュー" in out
    assert "注入ブロック" in out
    assert "サンプルフレーズ" in out


def test_preview_english_speech(capsys) -> None:
    assert main(["preview", "casual_en"]) == 0
    out = capsys.readouterr().out
    assert "casual_en" in out
    assert "injection block" in out


# ---------------------------------------------------------------------------
# rich rendering (A2) — optional dependency, gated on TTY / --plain / NO_COLOR
# ---------------------------------------------------------------------------

def test_list_plain_when_not_tty(capsys) -> None:
    # capsys は非 TTY なので rich は使われずプレーン出力になる (回帰防止)。
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "personality/ (42)" in out
    assert "  - tsundere" in out


def test_list_rich_table_when_forced(capsys, monkeypatch) -> None:
    pytest.importorskip("rich")
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    # rich Table のボックス罫線とヘッダ列名が出る。
    assert "category" in out
    assert "attribute" in out
    assert "tsundere" in out
    assert "│" in out or "┃" in out


def test_plain_flag_overrides_forced_rich(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    assert main(["--plain", "list"]) == 0
    out = capsys.readouterr().out
    assert "personality/ (42)" in out
    assert "┃" not in out


def test_no_color_disables_rich(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "personality/ (42)" in out
    assert "┃" not in out


def test_show_rich_panel_when_forced(capsys, monkeypatch) -> None:
    pytest.importorskip("rich")
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert main(["show", "tsundere"]) == 0
    out = capsys.readouterr().out
    assert "personality/tsundere" in out
    assert "core_traits" in out
    # Panel の枠線が出る。
    assert "╭" in out or "│" in out


# ---------------------------------------------------------------------------
# diff コマンド (B1)
# ---------------------------------------------------------------------------

def test_diff_basic(capsys) -> None:
    assert main(["diff", "tsundere", "dandere"]) == 0
    out = capsys.readouterr().out
    assert "diff: tsundere vs dandere" in out
    assert "relation: neutral" in out
    assert "[core_traits]" in out


def test_diff_conflict_relation(capsys) -> None:
    assert main(["diff", "yandere", "dandere"]) == 0
    assert "relation: conflict" in capsys.readouterr().out


def test_diff_cross_lang_speech_is_conflict(capsys) -> None:
    # ja speech と en speech は構造的 conflict。
    assert main(["diff", "keigo", "casual_en"]) == 0
    assert "relation: conflict" in capsys.readouterr().out


def test_diff_common_traits_detected(capsys) -> None:
    # tsundere と kuudere は core_traits に「素直になれない」を共有する。
    assert main(["diff", "tsundere", "kuudere"]) == 0
    out = capsys.readouterr().out
    assert "素直になれない" in out


def test_diff_category_prefix_accepted(capsys) -> None:
    assert main(["diff", "personality/tsundere", "speech/keigo"]) == 0
    assert "tsundere vs keigo" in capsys.readouterr().out


def test_diff_ja_locale(capsys) -> None:
    assert main(["--lang", "ja", "diff", "tsundere", "dandere"]) == 0
    out = capsys.readouterr().out
    assert "差分" in out
    assert "相性" in out


def test_diff_rich_table_when_forced(capsys, monkeypatch) -> None:
    pytest.importorskip("rich")
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert main(["diff", "tsundere", "dandere"]) == 0
    out = capsys.readouterr().out
    assert "tsundere" in out
    assert "│" in out or "┃" in out


def test_diff_unknown_attr_errors() -> None:
    assert main(["diff", "tsundere", "nonexistent_xyz"]) == 1


# ---------------------------------------------------------------------------
# blend/preview --suggest (B2)
# ---------------------------------------------------------------------------

def test_blend_suggest_prints_alternatives_to_stderr(capsys) -> None:
    assert main(["blend", "airhead", "intellectual", "--suggest"]) == 0
    captured = capsys.readouterr()
    # 注入ブロック (stdout) は汚さない
    assert "hersona" in captured.out
    assert "suggestions to resolve conflicts" in captured.err
    assert "chuunibyou" in captured.err


def test_blend_without_suggest_has_no_suggestions(capsys) -> None:
    assert main(["blend", "airhead", "intellectual"]) == 0
    err = capsys.readouterr().err
    assert "suggestions to resolve conflicts" not in err


def test_blend_suggest_no_conflict_is_silent(capsys) -> None:
    assert main(["blend", "tsundere", "keigo", "--suggest"]) == 0
    err = capsys.readouterr().err
    assert "suggestions to resolve conflicts" not in err


def test_preview_suggest_prints_alternatives(capsys) -> None:
    assert main(["preview", "airhead", "intellectual", "--suggest"]) == 0
    assert "suggestions to resolve conflicts" in capsys.readouterr().err


def test_blend_suggest_ja_locale(capsys) -> None:
    assert main(["--lang", "ja", "blend", "airhead", "intellectual", "--suggest"]) == 0
    assert "衝突を解消する代替案" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# save / presets / load (ROADMAP C)
# ---------------------------------------------------------------------------

def test_save_creates_preset(capsys) -> None:
    rc = main(["save", "my_blend", "tsundere", "keigo", "--weight", "strong"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Saved preset" in out
    assert "my_blend" in out


def test_save_then_presets_lists_it(capsys) -> None:
    assert main(["save", "my_blend", "tsundere", "keigo"]) == 0
    capsys.readouterr()
    assert main(["presets"]) == 0
    out = capsys.readouterr().out
    assert "my_blend" in out
    assert "tsundere + keigo" in out


def test_presets_none_when_empty(capsys) -> None:
    assert main(["presets"]) == 0
    assert "no presets saved yet" in capsys.readouterr().out


def test_save_then_load_replays_blend(capsys) -> None:
    assert main(["save", "my_blend", "tsundere", "keigo", "--weight", "strong"]) == 0
    capsys.readouterr()
    assert main(["load", "my_blend"]) == 0
    out = capsys.readouterr().out
    assert "preset: my_blend" in out
    assert "weight=strong" in out
    assert "tsundere" in out  # injection block rendered


def test_load_weight_override(capsys) -> None:
    assert main(["save", "my_blend", "tsundere", "keigo", "--weight", "strong"]) == 0
    capsys.readouterr()
    assert main(["load", "my_blend", "--weight", "mild"]) == 0
    assert "weight=mild" in capsys.readouterr().out


def test_save_duplicate_without_overwrite_errors(capsys) -> None:
    assert main(["save", "dup", "tsundere"]) == 0
    capsys.readouterr()
    rc = main(["save", "dup", "genki"])
    assert rc == 1
    assert "already exists" in capsys.readouterr().err


def test_save_overwrite_succeeds(capsys) -> None:
    assert main(["save", "dup", "tsundere"]) == 0
    capsys.readouterr()
    assert main(["save", "dup", "genki", "--overwrite"]) == 0
    capsys.readouterr()
    assert main(["load", "dup"]) == 0
    assert "genki" in capsys.readouterr().out


def test_save_bad_name_errors(capsys) -> None:
    rc = main(["save", "Bad-Name", "tsundere"])
    assert rc == 1
    assert "invalid preset name" in capsys.readouterr().err


def test_save_unknown_attribute_errors(capsys) -> None:
    rc = main(["save", "ok", "no_such_attr_xyz"])
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_save_conflict_warns_but_saves(capsys) -> None:
    rc = main(["save", "conflicted", "airhead", "intellectual"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "conflict" in captured.err
    assert "Saved preset" in captured.out


def test_load_missing_preset_errors(capsys) -> None:
    rc = main(["load", "nonexistent_preset"])
    assert rc == 1
    assert "preset not found" in capsys.readouterr().err


def test_presets_ja_locale(capsys) -> None:
    assert main(["save", "my_blend", "tsundere"]) == 0
    capsys.readouterr()
    assert main(["--lang", "ja", "presets"]) == 0
    assert "保存済みプリセット" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# shell completion (argcomplete) — ROADMAP C
# ---------------------------------------------------------------------------

def test_attribute_completer_filters_by_prefix() -> None:
    from hersona.cli.app import _attribute_completer

    assert _attribute_completer("ts") == ["tsugaru_ben", "tsundere"]
    out = _attribute_completer("")
    assert "tsundere" in out and "keigo" in out
    # sorted
    assert out == sorted(out)


def test_attribute_completer_no_match() -> None:
    from hersona.cli.app import _attribute_completer

    assert _attribute_completer("zzz_no_such") == []


def test_preset_completer_lists_saved(capsys) -> None:
    from hersona.cli.app import _preset_completer

    assert _preset_completer("") == []
    assert main(["save", "mypreset", "tsundere"]) == 0
    capsys.readouterr()
    assert _preset_completer("") == ["mypreset"]
    assert _preset_completer("my") == ["mypreset"]
    assert _preset_completer("x") == []


def test_try_argcomplete_is_noop_in_normal_run() -> None:
    """補完中でない通常実行では autocomplete は素通りし、main が普通に動く。"""
    from hersona.cli.app import _build_parser, _try_argcomplete

    # _ARGCOMPLETE 環境変数が無いので autocomplete は何もしない (例外なし)
    _try_argcomplete(_build_parser())
    assert main(["list"]) == 0


def test_cli_runs_when_argcomplete_absent(monkeypatch) -> None:
    """argcomplete 未インストールでも CLI は通常動作する (ImportError を握り潰す)。"""
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "argcomplete":
            raise ImportError("simulated missing argcomplete")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert main(["list"]) == 0


# ---------------------------------------------------------------------------
# export (ROADMAP C)
# ---------------------------------------------------------------------------

def test_export_json_cli(capsys) -> None:
    import json as _json

    assert main(["export", "tsundere", "keigo", "--weight", "strong"]) == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["hersona"]["names"] == ["tsundere", "keigo"]
    assert data["hersona"]["weight"] == "strong"


def test_export_messages_cli(capsys) -> None:
    import json as _json

    assert main(["export", "tsundere", "--format", "messages"]) == 0
    msgs = _json.loads(capsys.readouterr().out)
    assert msgs[0]["role"] == "system"


def test_export_markdown_cli(capsys) -> None:
    assert main(["export", "tsundere", "--format", "markdown"]) == 0
    out = capsys.readouterr().out
    assert "hersona" in out
    assert "core_traits" in out


def test_export_unknown_attribute_errors(capsys) -> None:
    assert main(["export", "no_such_attr_xyz"]) == 1
    assert "not found" in capsys.readouterr().err


# --- persistent --target (Claude Code / Codex / Cursor / Gemini) -----------


def test_persistent_target_claude_writes_file(tmp_path, capsys) -> None:
    out = tmp_path / "CLAUDE.md"
    rc = main(
        [
            "persistent", "tsundere", "keigo",
            "--target", "claude",
            "--output", str(out),
            "--weight", "strong",
        ]
    )
    assert rc == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# Persona (hersona)" in text
    assert "Hermes Agent ペルソナ定義" not in text


def test_persistent_target_codex_alias_agents(tmp_path) -> None:
    out = tmp_path / "AGENTS.md"
    assert main(["persistent", "tsundere", "--target", "agents", "--output", str(out)]) == 0
    assert out.exists()


def test_persistent_target_existing_needs_force(tmp_path, capsys) -> None:
    out = tmp_path / "GEMINI.md"
    assert main(["persistent", "tsundere", "--target", "gemini", "--output", str(out)]) == 0
    capsys.readouterr()
    # 2 回目は --force なしで失敗
    assert main(["persistent", "tsundere", "--target", "gemini", "--output", str(out)]) == 1
    capsys.readouterr()
    # --force で上書き成功
    assert main(
        ["persistent", "tsundere", "--target", "gemini", "--output", str(out), "--force"]
    ) == 0


def test_persistent_target_ignores_hermes_flags(tmp_path, capsys) -> None:
    out = tmp_path / "CLAUDE.md"
    rc = main(
        [
            "persistent", "tsundere",
            "--target", "claude",
            "--output", str(out),
            "--auto-config",
        ]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "auto-config" in err or "hermes" in err.lower()
