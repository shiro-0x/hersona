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
    assert "Available attributes (64)" in out
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
    assert "64 件" in capsys.readouterr().out
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
    assert "personality/ (20)" in out
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
    assert "personality/ (20)" in out
    assert "┃" not in out


def test_no_color_disables_rich(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HERSONA_FORCE_RICH", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "personality/ (20)" in out
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
