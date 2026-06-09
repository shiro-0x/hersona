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
    assert "33 件" in out
    assert "tsundere" in out


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
    assert "推薦結果" in out
    assert "tsundere" in out


def test_recommend_json(capsys) -> None:
    assert main(["recommend", "--answers", "distance=1", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "blend" in data
    assert "scores" in data


def test_recommend_apply_shows_block(capsys) -> None:
    assert main(["recommend", "--answers", "distance=1,speech=0", "--apply"]) == 0
    out = capsys.readouterr().out
    assert "注入ブロック" in out


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
    assert "保存しました" in capsys.readouterr().out
    # 直後に show で解決できる
    assert main(["show", "cli_made"]) == 0
    assert "personality/cli_made" in capsys.readouterr().out


def test_create_missing_required_flag_errors(capsys) -> None:
    rc = main(["create", "--category", "personality", "--name", "x"])
    assert rc == 1


def test_no_command_prints_help(capsys) -> None:
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()
