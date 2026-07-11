"""hersona CLI (hersona.cli.app) の回帰テスト。

非対話フラグ経路を中心に main(argv) を直接呼んで stdout を検証する。
ユーザー名前空間とダウンロード済み公開データキャッシュは tmp に向けて隔離する。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

# hersona.core.attach / compatibility resolve public data roots at import time.
# Keep CLI tests independent from a user's downloaded ~/.hermes/data cache.
os.environ.setdefault("HERSONA_DATA_DIR", str(Path(__file__).resolve().parent / ".empty-data"))

import pytest

from hersona.cli.app import main
from tests.catalog_counts import (
    PUBLIC_CATEGORY_COUNTS,
    cli_list_banner_en,
    cli_list_banner_ja_count_fragment,
)


@pytest.fixture(autouse=True)
def _isolate_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))
    monkeypatch.setenv("HERSONA_DATA_DIR", str(tmp_path / "data"))


def test_list(capsys) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert cli_list_banner_en() in out
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


def test_blend_with_use_case(capsys) -> None:
    assert main(["blend", "tsundere", "keigo", "--use-case", "programmer"]) == 0
    out = capsys.readouterr().out
    assert "## Operating Mode: Programmer" in out
    assert "Inspect relevant files before editing." in out


def test_export_humanize_reaches_output(capsys) -> None:
    assert main(
        ["export", "tsundere", "keigo", "--weight", "moderate", "--format", "markdown",
         "--no-persona-lock", "--humanize"]
    ) == 0
    out = capsys.readouterr().out
    assert "人間味" in out


def test_export_humanize_off_by_default(capsys) -> None:
    assert main(
        ["export", "tsundere", "keigo", "--weight", "moderate", "--format", "markdown",
         "--no-persona-lock"]
    ) == 0
    out = capsys.readouterr().out
    assert "人間味" not in out


def test_soul_has_no_humanize_flag() -> None:
    """SOUL.md 本文は render_blend(...).prompt を使わないため --humanize は登録しない。"""
    with pytest.raises(SystemExit):
        main(["soul", "tsundere", "--humanize", "--dry-run"])
def test_blend_style_examples(capsys) -> None:
    assert main(["blend", "tsundere", "keigo", "--style-examples", "2"]) == 0
    out = capsys.readouterr().out
    assert "## Style examples" in out


def test_blend_style_examples_default_off(capsys) -> None:
    assert main(["blend", "tsundere", "keigo"]) == 0
    out = capsys.readouterr().out
    assert "Style examples" not in out


def test_persistent_target_style_examples_warns(capsys, tmp_path) -> None:
    out_path = tmp_path / "CLAUDE.md"
    rc = main(
        ["persistent", "tsundere", "--target", "claude", "--style-examples", "2",
         "--output", str(out_path)]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "--style-examples" in err
    assert "claude" in err


def test_use_case_list_and_show(capsys) -> None:
    assert main(["use-case", "list"]) == 0
    out = capsys.readouterr().out
    assert "Available use cases" in out
    assert "programmer" in out

    assert main(["use-case", "show", "programmer"]) == 0
    out = capsys.readouterr().out
    assert "## Operating Mode: Programmer" in out
    assert "Do not claim success without observed command output." in out


def test_soul_dry_run_with_use_case(capsys) -> None:
    assert main(["soul", "tsundere", "keigo", "--use-case", "planner", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "<!-- use_case: planner -->" in out
    assert "## Operating Mode: Strategic Planner" in out


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


def test_recommend_export_stdout_is_payload_only(capsys) -> None:
    # --export (stdout) は成果物のみを流す (パイプでそのまま file に落とせる)。
    assert main(["recommend", "--answers", "distance=1,speech=0", "--export", "markdown"]) == 0
    out = capsys.readouterr().out
    assert "hersona attribute blend" in out
    assert "Recommendation" not in out  # 人間向けサマリは抑止される


def test_recommend_export_openai_assistants_is_valid_json(capsys) -> None:
    assert main(
        ["recommend", "--answers", "distance=1,speech=0", "--export", "openai_assistants"]
    ) == 0
    data = json.loads(capsys.readouterr().out)
    assert "instructions" in data
    assert data["metadata"]["hersona_weight"]


def test_recommend_export_output_writes_file(capsys, tmp_path) -> None:
    dest = tmp_path / "blend.json"
    assert main(
        [
            "recommend", "--answers", "distance=1,speech=0",
            "--export", "json", "--output", str(dest),
        ]
    ) == 0
    out = capsys.readouterr().out
    assert "Recommendation" in out  # ファイル出力時はサマリも表示
    assert str(dest) in out
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert "system_prompt" in data or "hersona" in data


def test_recommend_soul_dry_run_prints_soul(capsys) -> None:
    assert main(["recommend", "--answers", "distance=1,speech=0", "--soul", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "generated by hersona" in out
    assert "Recommendation" not in out


def test_recommend_soul_writes_and_protects(capsys, tmp_path) -> None:
    dest = tmp_path / "SOUL.md"
    argv = [
        "recommend", "--answers", "distance=1,speech=0",
        "--soul", "--soul-output", str(dest),
    ]
    assert main(argv) == 0
    assert dest.exists()
    assert "blend" in dest.read_text(encoding="utf-8")
    capsys.readouterr()
    # 2 回目は既定拒否 (--force なし)
    assert main(argv) == 1
    err = capsys.readouterr().err
    assert "--force" in err
    # --force で上書きできる
    assert main([*argv, "--force"]) == 0


def test_recommend_save_preset_roundtrip(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert main(
        ["recommend", "--answers", "distance=1,speech=0", "--save", "from_quiz"]
    ) == 0
    out = capsys.readouterr().out
    assert "from_quiz" in out
    assert main(["load", "from_quiz"]) == 0
    assert "hersona attribute blend" in capsys.readouterr().out


def test_recommend_json_rejects_bridge_flags(capsys) -> None:
    assert main(
        ["recommend", "--answers", "distance=1", "--json", "--export", "markdown"]
    ) == 2
    assert "--json" in capsys.readouterr().err


def test_bench_demo_reports_maintenance_rate(capsys) -> None:
    assert main(["bench", "tsundere", "keigo", "--demo", "--turns", "4"]) == 0
    out = capsys.readouterr().out
    assert "Bench" in out
    assert "Maintenance rate" in out
    assert "Mean score" in out


def test_bench_demo_json(capsys) -> None:
    assert main(["bench", "tsundere", "keigo", "--demo", "--turns", "3", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["blend"] == ["tsundere", "keigo"]
    assert "maintenance_rate" in data
    assert "decay" in data


def test_bench_transcript_file(capsys, tmp_path) -> None:
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(
        json.dumps(["こんにちは、失礼します。", "承知いたしました。"], ensure_ascii=False),
        encoding="utf-8",
    )
    assert main(
        ["bench", "tsundere", "keigo", "--transcript", str(transcript_path)]
    ) == 0
    assert "Bench" in capsys.readouterr().out


def test_bench_with_scenario_label(capsys, tmp_path) -> None:
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(json.dumps(["こんにちは。"], ensure_ascii=False), encoding="utf-8")
    assert main(
        [
            "bench", "tsundere", "keigo",
            "--transcript", str(transcript_path),
            "--scenario", "benchmarks/scenarios/casual_greeting_ja.yaml",
        ]
    ) == 0
    assert "casual_greeting_ja" in capsys.readouterr().out


def test_bench_cost_only(capsys) -> None:
    assert main(["bench", "tsundere", "keigo", "--cost-only", "--weight", "strong"]) == 0
    out = capsys.readouterr().out
    assert "chars" in out
    assert "tokens" in out


def test_bench_requires_transcript_xor_demo(capsys) -> None:
    assert main(["bench", "tsundere", "keigo"]) == 1
    err = capsys.readouterr().err
    assert "--transcript" in err and "--demo" in err


def test_bench_rejects_both_transcript_and_demo(capsys, tmp_path) -> None:
    transcript_path = tmp_path / "t.json"
    transcript_path.write_text("[]", encoding="utf-8")
    assert main(
        ["bench", "tsundere", "keigo", "--transcript", str(transcript_path), "--demo"]
    ) == 1


def _write_attack_transcript(tmp_path, n: int = 12):
    transcript_path = tmp_path / "attack_transcript.json"
    transcript_path.write_text(
        json.dumps(["べ、別にあなたのためじゃないんだからね!"] * n, ensure_ascii=False),
        encoding="utf-8",
    )
    return transcript_path


def test_bench_transcript_with_attack_scenario_prints_lock_resistance(capsys, tmp_path) -> None:
    transcript_path = _write_attack_transcript(tmp_path)
    assert main(
        [
            "bench", "tsundere", "keigo",
            "--transcript", str(transcript_path),
            "--scenario", "benchmarks/scenarios/persona_override_attack_ja.yaml",
        ]
    ) == 0
    assert "Lock resistance" in capsys.readouterr().out


def test_bench_json_includes_lock_resistance(capsys, tmp_path) -> None:
    transcript_path = _write_attack_transcript(tmp_path)
    assert main(
        [
            "bench", "tsundere", "keigo",
            "--transcript", str(transcript_path),
            "--scenario", "benchmarks/scenarios/persona_override_attack_ja.yaml",
            "--json",
        ]
    ) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["attack_turns"] == [2, 4, 5, 7, 8, 10]
    assert data["lock_resistance_rate"] is not None


def test_bench_demo_with_attack_scenario_omits_lock_resistance(capsys) -> None:
    # デモ transcript はシナリオ turns と対応しないため攻撃マーカーを適用しない。
    assert main(
        [
            "bench", "tsundere", "keigo", "--demo", "--turns", "4",
            "--scenario", "benchmarks/scenarios/persona_override_attack_ja.yaml",
        ]
    ) == 0
    assert "Lock resistance" not in capsys.readouterr().out


def test_bench_transcript_scenario_length_mismatch_warns(capsys, tmp_path) -> None:
    transcript_path = _write_attack_transcript(tmp_path, n=1)
    assert main(
        [
            "bench", "tsundere", "keigo",
            "--transcript", str(transcript_path),
            "--scenario", "benchmarks/scenarios/persona_override_attack_ja.yaml",
        ]
    ) == 0
    assert "warning" in capsys.readouterr().err


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
    assert cli_list_banner_ja_count_fragment() in capsys.readouterr().out
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
    assert f"personality/ ({PUBLIC_CATEGORY_COUNTS['personality']})" in out
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
    assert f"personality/ ({PUBLIC_CATEGORY_COUNTS['personality']})" in out
    assert "┃" not in out


def test_no_color_disables_rich(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    personality_count = PUBLIC_CATEGORY_COUNTS["personality"]
    assert f"personality/ ({personality_count})" in out
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

    assert _attribute_completer("ts") == ["tsugaru_ben", "tsukkomi", "tsundere"]
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
    # v1.8.0: persona_lock が既定で blend に付加される (--no-persona-lock でオフ)
    assert data["hersona"]["names"] == ["tsundere", "keigo", "persona_lock"]
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


def test_persistent_target_compact_warns_and_has_no_effect(tmp_path, capsys) -> None:
    # sharpen-and-grow A-4: --target 出力は response_style_directive を含まないため
    # --compact は無効。警告のみ出し、出力内容は変わらない。
    out_full = tmp_path / "CLAUDE_full.md"
    out_compact = tmp_path / "CLAUDE_compact.md"
    assert main(
        ["persistent", "tsundere", "keigo", "--target", "claude", "--output", str(out_full)]
    ) == 0
    capsys.readouterr()
    rc = main(
        [
            "persistent", "tsundere", "keigo",
            "--target", "claude", "--output", str(out_compact), "--compact",
        ]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "compact" in err.lower()
    # 生成タイムスタンプ (ヘッダ・フッター双方) を除けば内容は完全一致する。
    ts_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
    full_text = ts_pattern.sub("<TS>", out_full.read_text(encoding="utf-8"))
    compact_text = ts_pattern.sub("<TS>", out_compact.read_text(encoding="utf-8"))
    assert full_text == compact_text


# --- compact (sharpen-and-grow A-4) -----------------------------------------


def test_blend_compact_flag_shrinks_output(capsys) -> None:
    assert main(["blend", "tsundere", "keigo"]) == 0
    full = capsys.readouterr().out
    assert main(["blend", "tsundere", "keigo", "--compact"]) == 0
    compact = capsys.readouterr().out
    assert len(compact) < len(full)


def test_export_markdown_compact_flag_shrinks_output(capsys) -> None:
    assert main(["export", "tsundere", "keigo", "--format", "markdown"]) == 0
    full = capsys.readouterr().out
    assert main(["export", "tsundere", "keigo", "--format", "markdown", "--compact"]) == 0
    compact = capsys.readouterr().out
    assert len(compact) < len(full)


def test_soul_has_no_compact_flag(capsys) -> None:
    # argparse レベルで未知フラグ扱いになるため SystemExit(2) を送出する。
    with pytest.raises(SystemExit) as excinfo:
        main(["soul", "tsundere", "--dry-run", "--compact"])
    assert excinfo.value.code == 2
    assert "--compact" in capsys.readouterr().err


# --- PR-B W1: personas サブコマンド ---------------------------------------


def test_personas_list_empty(capsys, tmp_path: Path) -> None:
    """personas/ が空 (or 不在) でも list は exit 0、件数を表示。"""
    # tmp に personas/ を作らない → 0 件カタログ
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "hersona.core.personas.PUBLIC_PERSONAS_ROOT",
            tmp_path / "personas_empty",
        )
        rc = main(["personas", "list", "--plain"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "(0)" in out
    finally:
        monkeypatch.undo()


def test_personas_list_json(capsys, tmp_path: Path) -> None:
    """--json で機械可読出力がでる。"""
    import yaml

    pack_path = tmp_path / "keigo_support.yaml"
    pack_path.write_text(
        yaml.safe_dump(
            {
                "persona_name": "keigo_support",
                "display_name": "Courteous Support",
                "description": "Courteous customer-support persona.",
                "blend": ["personality/diligent", "speech/keigo"],
                "weight": "moderate",
                "use_case": "customer_support",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "hersona.core.personas.PUBLIC_PERSONAS_ROOT", tmp_path
        )
        rc = main(["personas", "list", "--plain", "--json"])
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["persona_name"] == "keigo_support"
        assert data[0]["use_case"] == "customer_support"
    finally:
        monkeypatch.undo()


def test_personas_show_not_found_returns_1(capsys) -> None:
    """未存在パックは exit 1、エラー出力に「not found」相当。"""
    rc = main(["personas", "show", "does_not_exist", "--plain"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower() or "見つかりません" in err


def test_personas_show_ja_localized_not_found(capsys) -> None:
    """--lang ja でエラーメッセージも日本語化。"""
    rc = main(["personas", "show", "does_not_exist", "--lang", "ja", "--plain"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "見つかりません" in err


def test_personas_install_dry_run_prints_yaml_block(capsys, tmp_path: Path) -> None:
    """--dry-run は config.yaml ブロックを表示するだけで書き込まない。"""
    import yaml

    pack_path = tmp_path / "keigo_support.yaml"
    pack_path.write_text(
        yaml.safe_dump(
            {
                "persona_name": "keigo_support",
                "display_name": "Courteous Support",
                "description": "Courteous customer-support persona.",
                "blend": ["personality/diligent", "speech/keigo"],
                "weight": "moderate",
                "use_case": "customer_support",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "hersona.core.personas.PUBLIC_PERSONAS_ROOT", tmp_path
        )
        # HOME を tmp_path に向けて、persistent が config.yaml を探しても安全な場所に
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        rc = main(["personas", "install", "keigo_support", "--dry-run", "--plain"])
        out = capsys.readouterr().out
        assert rc == 0
        # YAML ブロックに personalities: がある
        assert "personalities:" in out
        assert "keigo_support:" in out
    finally:
        monkeypatch.undo()


def test_personas_install_validation_error_returns_1(capsys, tmp_path: Path) -> None:
    """schema NG の pack は install 時に exit 1。"""
    import yaml

    pack_path = tmp_path / "bad.yaml"
    pack_path.write_text(
        yaml.safe_dump(
            {
                "persona_name": "bad",
                "display_name": "Bad",
                "description": "missing blend",
                # blend がない → schema NG
                "weight": "moderate",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "hersona.core.personas.PUBLIC_PERSONAS_ROOT", tmp_path
        )
        rc = main(["personas", "install", "bad", "--dry-run", "--plain"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "validation" in err.lower() or "検証" in err
    finally:
        monkeypatch.undo()


def test_personas_install_unknown_returns_1(capsys) -> None:
    """存在しないパック名の install は exit 1。"""
    rc = main(["personas", "install", "no_such_pack", "--dry-run", "--plain"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower() or "見つかりません" in err


def test_personas_bulk_warning_at_5_plus(capsys, tmp_path: Path) -> None:
    """5 件以上の install は合計サイズ警告 (stderr)。"""
    import yaml

    for i in range(5):
        (tmp_path / f"pack_{i}.yaml").write_text(
            yaml.safe_dump(
                {
                    "persona_name": f"pack_{i}",
                    "display_name": f"Pack {i}",
                    "description": "x",
                    "blend": ["personality/diligent"],
                    "weight": "moderate",
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "hersona.core.personas.PUBLIC_PERSONAS_ROOT", tmp_path
        )
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        names = " ".join(f"pack_{i}" for i in range(5))
        rc = main(["personas", "install"] + names.split() + ["--dry-run", "--plain"])
        # 5 件以上でも dry-run で成立 (size 警告は stderr)
        assert rc == 0
        err = capsys.readouterr().err
        assert "5 packs" in err or "5 件" in err
    finally:
        monkeypatch.undo()


def test_recommend_install_persona_registers_pack(capsys, tmp_path: Path, monkeypatch) -> None:
    """`hersona recommend --install-persona NAME` がペルソナパック登録まで通す。

    設計書 §5: 診断結果 blend + weight_suggestion を agent.personalities.NAME に登録。
    ここでは HOME を tmp に向けて config.yaml の自動書き込みは skip し、
    SOUL.md も書かない (without_soul=True がデフォルト)。
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    rc = main(
        [
            "recommend",
            "--answers", "distance=1,speech=0,role=1",
            "--install-persona", "from_recommend",
            "--lang", "en",
            "--plain",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "registered persona pack: from_recommend" in out


def test_recommend_install_persona_rejects_json(capsys) -> None:
    """`--json` + `--install-persona` は排他 (exit 2)。"""
    rc = main(
        [
            "recommend",
            "--answers", "distance=1,speech=0,role=1",
            "--json",
            "--install-persona", "x",
            "--plain",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "json" in err.lower() or "排他" in err or "exclusive" in err.lower()
