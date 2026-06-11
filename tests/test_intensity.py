"""強度指標 (hersona.core.intensity) の回帰テスト。

カバー範囲 (IMPLEMENTATION_GUIDE §4.2 Step 4):
- speech 属性無しブレンド → None
- speech ありで語尾多用 → endings_rate が高い
- 作為テキストで strong バンド、平淡で under
- verify の status 判定 (pass / under / over)
- expected_band の各レベルの境界
- CLI: `hersona measure` が speech 無しで skip / speech ありで stdout 出力
- 実データ参照テストは public_root / user_root を渡して公開属性で実行
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.cli.app import main
from hersona.core.intensity import (
    IntensityReport,
    content_language,
    expected_band,
    format_report,
    measure_intensity,
    skip_reason,
    verify,
)
from hersona.core.weight import WeightLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def _attrs(names: list[str]) -> list[dict]:
    """公開 attributes/ から dict 群を読み込む (テスト用ヘルパー)。"""
    from hersona.core.attach import load_attribute

    return [
        load_attribute(n, public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
        for n in names
    ]


# --- expected_band ----------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (WeightLevel.NONE, (0, 20)),
        (WeightLevel.MILD, (20, 45)),
        (WeightLevel.MODERATE, (45, 70)),
        (WeightLevel.STRONG, (70, 100)),
        ("none", (0, 20)),
        ("strong", (70, 100)),
    ],
)
def test_expected_band_levels(level, expected) -> None:
    assert expected_band(level) == expected


def test_expected_band_unknown_raises() -> None:
    with pytest.raises(ValueError):
        expected_band("intense")  # type: ignore[arg-type]


# --- measure_intensity: speech 無し → None ---------------------------------


def test_measure_returns_none_when_no_speech_attribute() -> None:
    """tsundere は personality なので speech が無く None。"""
    attrs = _attrs(["tsundere"])
    assert measure_intensity("べ、別に……そんなつもりはないけど", attrs) is None


def test_measure_returns_none_for_archetype_only() -> None:
    """heroine 単体 (archetype) も speech が無く None。"""
    attrs = _attrs(["heroine"])
    assert measure_intensity("こんにちは", attrs) is None


# --- measure_intensity: speech あり ----------------------------------------


def test_measure_high_endings_rate() -> None:
    """kyoto_ben の語尾を 3 文中 2 文一致 + 口癖 1 件のケース。

    実テキスト: 「おいでやす」(語尾マッチなし) / 「どすえ」(語尾マッチ「え」) /
                「ます。」(語尾マッチなし) → 1/3 ≈ 0.333。+「おいでやす」口癖 1 件。
    """
    attrs = _attrs(["kyoto_ben"])
    text = "ようおいでやす。今日はええ天気どすえ。そろそろ帰らはります。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.sentence_count == 3
    assert report.endings_rate == pytest.approx(1 / 3)
    assert report.catchphrase_hits >= 1  # 「おいでやす」
    assert 0 < report.score < 100.0


def test_measure_low_endings_rate() -> None:
    """kyoto_ben だけ指定で語尾ゼロのテキスト。"""
    attrs = _attrs(["kyoto_ben"])
    text = "こんにちは。今日もよろしくお願いします。それではまた。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.endings_rate == 0.0
    assert report.catchphrase_hits == 0
    assert report.score == pytest.approx(0.0)


def test_measure_normalizes_wave_dash_endings() -> None:
    """sentence_endings が「〜どす」表記でも、波ダッシュを除去して照合する。"""
    # 動作確認: kyoto_ben の sentence_endings は ['〜どす', ...] 形式
    attrs = _attrs(["kyoto_ben"])
    assert any(e.startswith("〜") for e in attrs[0].get("sentence_endings", []))
    text = "ほんまにええお天気どす。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.endings_rate == 1.0


def test_measure_empty_text() -> None:
    attrs = _attrs(["kyoto_ben"])
    report = measure_intensity("", attrs)
    assert report is not None
    assert report.sentence_count == 0
    assert report.score == 0.0


# --- verify: status 判定 ----------------------------------------------------


def test_verify_pass_in_band() -> None:
    """moderate 期待 (45-70) に収まるスコア。"""
    attrs = _attrs(["kyoto_ben"])
    text = "ようおいでやす。ええ天気どすえ。かなんわあ。"
    report = verify(text, attrs, WeightLevel.MODERATE)
    assert report is not None
    assert report.band == (45, 70)
    # 3 文中 3 文一致 + 口癖 1+ → 60 + α で moderate 帯
    if 45 <= report.score <= 70:
        assert report.status == "pass"
    elif report.score < 45:
        assert report.status == "under"
    else:
        assert report.status == "over"


def test_verify_under_status() -> None:
    """strong 期待で語尾ゼロのテキスト → under 警告対象。"""
    attrs = _attrs(["kyoto_ben"])
    text = "こんにちは。さようなら。"
    report = verify(text, attrs, WeightLevel.STRONG)
    assert report is not None
    assert report.band == (70, 100)
    assert report.score < 70
    assert report.status == "under"


def test_verify_pass_at_lower_boundary() -> None:
    """score がちょうど band 下端 (lo) のとき pass 判定になる。

    kyoto_ben の語尾を 1 文だけ完全一致 + 口癖 0 件:
      score = 100 * (0.6 * 1.0 + 0.4 * 0) = 60 → moderate (45-70) で pass
    """
    attrs = _attrs(["kyoto_ben"])
    # 「どすえ。」は語尾「え」に一致 (1/1)。「よろしおすなあ」は口癖だが語尾不一致。
    # 口癖が含まれると density > 0 になるので、語尾だけ効く文を選ぶ。
    # → 「どす。」単独 (語尾「どす」一致、口癖ゼロ)
    text = "ええ天気どす。"
    report = verify(text, attrs, WeightLevel.MODERATE)
    assert report is not None
    assert report.endings_rate == pytest.approx(1.0)
    assert report.catchphrase_hits == 0
    assert report.score == pytest.approx(60.0)
    assert 45 <= report.score <= 70
    assert report.status == "pass"


def test_verify_over_status() -> None:
    """none 期待 (0-20) で高スコアのテキスト → over。"""
    attrs = _attrs(["kyoto_ben"])
    text = "ようおいでやす。ええ天気どすえ。堪忍やで。"
    report = verify(text, attrs, WeightLevel.NONE)
    assert report is not None
    assert report.score > 20
    assert report.status == "over"


def test_verify_returns_none_without_speech() -> None:
    attrs = _attrs(["tsundere"])
    assert verify("べ、別に", attrs, WeightLevel.STRONG) is None


# --- format_report ---------------------------------------------------------


def test_format_report_under_marks_warning() -> None:
    report = IntensityReport(
        score=10.0,
        endings_rate=0.1,
        catchphrase_hits=0,
        sentence_count=2,
        band=(70, 100),
        status="under",
    )
    out = format_report(report, "strong")
    assert "10/100" in out
    assert "strong(70-100)" in out
    assert "under" in out
    assert "⚠" in out


def test_format_report_pass_marks_check() -> None:
    report = IntensityReport(
        score=76.0,
        endings_rate=0.8,
        catchphrase_hits=3,
        sentence_count=4,
        band=(70, 100),
        status="pass",
    )
    out = format_report(report, "strong")
    assert "76/100" in out
    assert "status=pass" in out
    assert "✓" in out


# --- CLI: hersona measure ---------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HERSONA_USER_DIR", str(tmp_path / "userattrs"))


def test_cli_measure_speech_full_match(capsys) -> None:
    """speech ありで band 内なら exit 0 かつ stdout にレポート。"""
    rc = main(["measure", "kyoto_ben", "--weight", "strong", "--text", "ようおいでやすどす"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "intensity" in out
    assert "kyoto_ben" not in out  # レポート行は数値の話


def test_cli_measure_speech_none_skips(capsys) -> None:
    """speech 無しブレンドは skip メッセージ + exit 0。"""
    rc = main(["measure", "tsundere", "--weight", "moderate", "--text", "べ、別に……"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "skip" in out


# --- Phase 4: 言語認識 -----------------------------------------------------


def _speech_ja() -> dict:
    return {
        "attribute_category": "speech",
        "attribute_name": "demo",
        "content_lang": "ja",
        "sentence_endings": ["です", "ます"],
        "catchphrases": [],
    }


def test_content_language_defaults_to_ja() -> None:
    # content_lang 未指定の speech は ja 既定。
    bare = {"attribute_category": "speech", "sentence_endings": ["だ"]}
    assert content_language([bare]) == "ja"
    assert content_language([_speech_ja()]) == "ja"


def test_content_language_reads_en() -> None:
    en_speech = {"attribute_category": "speech", "content_lang": "en", "sentence_endings": []}
    assert content_language([en_speech]) == "en"


def test_skip_reason_no_speech() -> None:
    assert skip_reason("anything", [{"attribute_category": "personality"}]) == "no_speech"


def test_skip_reason_lang_mismatch_for_english_text_on_ja_persona() -> None:
    # ja コンテンツに英語出力 → lang_mismatch で skip。
    assert skip_reason("Hello there, how are you?", [_speech_ja()]) == "lang_mismatch"


def test_skip_reason_none_for_matching_japanese_text() -> None:
    assert skip_reason("です。ます。", [_speech_ja()]) is None


def test_report_carries_lang() -> None:
    report = measure_intensity("です。ます。", [_speech_ja()])
    assert report is not None
    assert report.lang == "ja"


def test_cli_measure_lang_mismatch_skips(capsys) -> None:
    # ja 人格に英語テキストを渡すと言語不一致で skip (exit 0)。
    rc = main(["measure", "kyoto_ben", "--weight", "strong", "--text", "Hello, nice weather today."])
    assert rc == 0
    assert "skip" in capsys.readouterr().out.lower()


# --- W1 Step 2: 言語拘束コンテンツの解決 -----------------------------------


def test_resolve_content_field_base_language_is_native() -> None:
    from hersona.core.intensity import resolve_content_field

    # ja 属性 (content_lang 未指定) を ja で解決 → BASE がネイティブ
    ja_attr = {"catchphrases": ["やあ"], "tone": "明るい"}
    assert resolve_content_field(ja_attr, "catchphrases", "ja") == (["やあ"], True)
    # en speech (content_lang=en) の BASE は en で解決 → ネイティブ
    en_attr = {"content_lang": "en", "catchphrases": ["Yo!"]}
    assert resolve_content_field(en_attr, "catchphrases", "en") == (["Yo!"], True)


def test_resolve_content_field_uses_content_i18n() -> None:
    from hersona.core.intensity import resolve_content_field

    attr = {
        "catchphrases": ["やあ"],
        "content_i18n": {"en": {"catchphrases": ["Hey there!"]}},
    }
    assert resolve_content_field(attr, "catchphrases", "en") == (["Hey there!"], True)


def test_resolve_content_field_missing_lang_marks_non_native() -> None:
    from hersona.core.intensity import resolve_content_field

    # en 要求だが en コンテンツ無し → BASE(ja) と is_native=False (呼び出し側で除外)
    attr = {"catchphrases": ["やあ"]}
    value, native = resolve_content_field(attr, "catchphrases", "en")
    assert value == ["やあ"]
    assert native is False


# --- Phase 5: 英語コンテンツの採点 -----------------------------------------


def _speech_en() -> dict:
    return {
        "attribute_category": "speech",
        "attribute_name": "demo_en",
        "content_lang": "en",
        "lexical_markers": ["gonna", "yeah", "y'know"],
        "catchphrases": ["No worries!"],
    }


def test_en_content_language_and_skip_reason() -> None:
    assert content_language([_speech_en()]) == "en"
    # en コンテンツ + 英語テキスト → 測定可 (skip しない)
    assert skip_reason("Yeah, I'm gonna go. No worries!", [_speech_en()]) is None
    # en コンテンツに日本語テキスト → 言語不一致
    assert skip_reason("こんにちは。元気ですか。", [_speech_en()]) == "lang_mismatch"


def test_en_intensity_scores_lexical_markers() -> None:
    # マーカーを多用した英語テキストは高スコア。
    high = measure_intensity("Yeah, I'm gonna go. Y'know, no worries!", [_speech_en()])
    assert high is not None
    assert high.lang == "en"
    assert high.endings_rate > 0  # マーカーを含む文がある
    # マーカーを含まない英語テキストは低スコア。
    low = measure_intensity("The meeting starts at noon. Please be on time.", [_speech_en()])
    assert low is not None
    assert low.score < high.score


def test_cli_measure_english_persona_scores(capsys) -> None:
    rc = main(
        ["measure", "casual_en", "--weight", "moderate", "--text", "Yeah, I'm gonna grab food, y'know?"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "intensity" in out  # skip されず採点行が出る


def test_cli_measure_under_warns_stderr(capsys) -> None:
    """under のとき stderr に警告、exit code は 0。"""
    rc = main(
        [
            "measure",
            "kyoto_ben",
            "--weight",
            "strong",
            "--text",
            "こんにちは。よろしくお願いします。",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "⚠" in captured.err
    assert "under" in captured.out


def test_cli_measure_input_file(capsys, tmp_path) -> None:
    """--input でファイルから読み込んで採点。"""
    f = tmp_path / "out.txt"
    f.write_text("ようおいでやすどす。ええ天気やんせ。", encoding="utf-8")
    rc = main(["measure", "kyoto_ben", "--weight", "moderate", "--input", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "intensity" in out


def test_cli_measure_missing_text_and_input_errors(capsys) -> None:
    """--input も --text も無いと ValueError → exit 1。"""
    rc = main(["measure", "kyoto_ben", "--weight", "moderate"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--input" in err or "--text" in err


def test_cli_measure_unknown_attribute_errors(capsys) -> None:
    """存在しない属性名で load_attribute が KeyError → exit 1。"""
    rc = main(["measure", "no_such_attr", "--text", "x"])
    assert rc == 1
