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
    pre_response_check_prompt,
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

    kyoto_ben (first_person あり) の語尾を 1 文だけ完全一致 + 口癖 0 件 + 一人称 0 件:
      score = 100 * (0.45 * 1.0 + 0.30 * 0 + 0.25 * 0) = 45 → moderate (45-70) の
      下端ちょうどで pass。
    """
    attrs = _attrs(["kyoto_ben"])
    # 「どすえ。」は語尾「え」に一致 (1/1)。「よろしおすなあ」は口癖だが語尾不一致。
    # 口癖が含まれると density > 0 になるので、語尾だけ効く文を選ぶ。
    # → 「どす。」単独 (語尾「どす」一致、口癖ゼロ、一人称「うち」も不出現)
    text = "ええ天気どす。"
    report = verify(text, attrs, WeightLevel.MODERATE)
    assert report is not None
    assert report.endings_rate == pytest.approx(1.0)
    assert report.catchphrase_hits == 0
    assert report.first_person_hits == 0
    assert report.score == pytest.approx(45.0)
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


# --- A-3 (sharpen-and-grow): zh / ko コンテンツの採点 ------------------------


def _speech_zh() -> dict:
    return {
        "attribute_category": "speech",
        "attribute_name": "demo_zh",
        "content_lang": "zh",
        "lexical_markers": ["嗯", "嘛", "啦", "吧"],
        "catchphrases": ["没事没事。"],
    }


def _speech_ko() -> dict:
    return {
        "attribute_category": "speech",
        "attribute_name": "demo_ko",
        "content_lang": "ko",
        "lexical_markers": ["진짜", "그냥", "가자"],
        "catchphrases": ["어, 진짜?"],
    }


def test_zh_content_language_and_skip_reason() -> None:
    assert content_language([_speech_zh()]) == "zh"
    # zh コンテンツ + 中国語テキスト (漢字のみ、仮名/ハングル無し) → 測定可
    assert skip_reason("嗯，行吧，没事没事。", [_speech_zh()]) is None
    # zh コンテンツに仮名混入 (日本語) → 言語不一致
    assert skip_reason("こんにちは、元気ですか。", [_speech_zh()]) == "lang_mismatch"
    # zh コンテンツにハングル混入 (韓国語) → 言語不一致
    assert skip_reason("진짜 그래?", [_speech_zh()]) == "lang_mismatch"


def test_ko_content_language_and_skip_reason() -> None:
    assert content_language([_speech_ko()]) == "ko"
    # ko コンテンツ + ハングルテキスト → 測定可
    assert skip_reason("어, 진짜? 그냥 가자.", [_speech_ko()]) is None
    # ko コンテンツにハングルが無い (漢字/仮名のみ) → 言語不一致
    assert skip_reason("こんにちは、元気ですか。", [_speech_ko()]) == "lang_mismatch"
    assert skip_reason("你好，好久不见。", [_speech_ko()]) == "lang_mismatch"


def test_zh_intensity_scores_lexical_markers() -> None:
    high = measure_intensity("嗯，行吧。没事没事，别提了嘛。", [_speech_zh()])
    assert high is not None
    assert high.lang == "zh"
    assert high.endings_rate > 0
    low = measure_intensity("今天天气很好。我们去公园散步。", [_speech_zh()])
    assert low is not None
    assert low.score < high.score


def test_ko_intensity_scores_lexical_markers() -> None:
    high = measure_intensity("어, 진짜? 그냥 가자, 가자.", [_speech_ko()])
    assert high is not None
    assert high.lang == "ko"
    assert high.endings_rate > 0
    low = measure_intensity("오늘 날씨가 좋습니다.", [_speech_ko()])
    assert low is not None
    assert low.score < high.score


def test_cli_measure_zh_persona_scores(capsys) -> None:
    rc = main(
        ["measure", "mandarin_casual", "--weight", "moderate", "--text", "嗯，行吧，没事没事，别提了嘛。"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "intensity" in out


def test_cli_measure_ko_persona_scores(capsys) -> None:
    rc = main(
        ["measure", "banmal", "--weight", "moderate", "--text", "어, 진짜? 그냥 가자, 가자."]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "intensity" in out


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


def test_cli_measure_check_prompt_naturalness_appends_section(capsys) -> None:
    """--check-prompt --naturalness で AI 臭自己点検節がプロンプト末尾に付く。"""
    rc = main(
        ["measure", "tsundere", "--weight", "moderate", "--check-prompt", "--naturalness"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "sounds AI-generated" in out


def test_cli_measure_check_prompt_without_naturalness_omits_section(capsys) -> None:
    rc = main(["measure", "tsundere", "--weight", "moderate", "--check-prompt"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "sounds AI-generated" not in out


def test_cli_measure_strict_naturalness_appends_section_to_stderr(capsys) -> None:
    """under 時の --strict 復旧プロンプトにも --naturalness で自己点検節が付く。"""
    rc = main(
        [
            "measure",
            "kyoto_ben",
            "--weight",
            "strong",
            "--text",
            "こんにちは。よろしくお願いします。",
            "--strict",
            "--naturalness",
        ]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "sounds AI-generated" in err


def test_cli_measure_unknown_attribute_errors(capsys) -> None:
    """存在しない属性名で load_attribute が KeyError → exit 1。"""
    rc = main(["measure", "no_such_attr", "--text", "x"])
    assert rc == 1


# --- B4: first_person 3 軸目採点 -------------------------------------------


def _speech_with_first_person(**kwargs: object) -> dict:
    base = {
        "attribute_category": "speech",
        "attribute_name": "fp_demo",
        "content_lang": "ja",
        "sentence_endings": [],
        "catchphrases": [],
    }
    base.update(kwargs)
    return base


def test_first_person_only_attr_is_measurable() -> None:
    """sentence_endings が無くても first_person があれば skip しない。"""
    attr = _speech_with_first_person(first_person="ボク")
    assert skip_reason("ボク、行くよ。", [attr]) is None
    report = measure_intensity("ボク、行くよ。", [attr])
    assert report is not None
    assert report.first_person_hits >= 1


def test_first_person_no_signal_still_skips() -> None:
    """first_person も sentence_endings も無い speech は skip。"""
    attr = _speech_with_first_person()  # no first_person, no endings
    assert skip_reason("こんにちは。", [attr]) == "no_speech"
    assert measure_intensity("こんにちは。", [attr]) is None


def test_first_person_hit_count() -> None:
    """first_person トークン出現回数が正確に計上される。"""
    attr = _speech_with_first_person(first_person="オレ / 俺")
    text = "オレが言った。俺はここにいる。そして俺は強い。"
    report = measure_intensity(text, [attr])
    assert report is not None
    assert report.first_person_hits == 3  # オレ×1 + 俺×2


def test_washi_measurable_with_three_axes(capsys) -> None:
    """washi は sentence_endings + first_person の 3 軸採点。"""
    attrs = _attrs(["washi"])
    text = "わしの若い頃はのう……焦りこそが敵じゃ。わしはそう思うぞ。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.first_person_hits >= 1
    assert report.endings_rate > 0  # 「〜じゃ」等一致
    # metric v2: 全軸 cadence 飽和の模範テキストは満点 100 になりうる
    assert 0 < report.score <= 100


def test_ore_boy_measurable_with_first_person(capsys) -> None:
    """ore_boy は sentence_endings が無いが first_person があるため測定できる。"""
    attrs = _attrs(["ore_boy"])
    text = "オレが守る。オレを誰だと思ってやがる。テメェのことはオレが信じてる。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.first_person_hits >= 2
    assert report.score > 0


def test_first_person_in_format_report() -> None:
    """format_report の出力に first_person_hits が含まれる。"""
    report = IntensityReport(
        score=55.0,
        endings_rate=0.5,
        catchphrase_hits=1,
        sentence_count=2,
        band=(45, 70),
        status="pass",
        first_person_hits=3,
    )
    out = format_report(report, "moderate")
    assert "55/100" in out
    assert "3" in out  # first_person_hits


# --- pre_response_check_prompt ---------------------------------------------


def test_pre_response_check_prompt_strong_contains_4_bullets() -> None:
    out = pre_response_check_prompt(["tsundere"], WeightLevel.STRONG)
    for n in ("1.", "2.", "3.", "4."):
        assert n in out
    assert "Make the traits clearly visible" in out


def test_pre_response_check_prompt_ja_uses_japanese_text() -> None:
    out = pre_response_check_prompt(["tsundere"], "strong", lang="ja")
    for word in ("口癖", "文末", "強度"):
        assert word in out


def test_pre_response_check_prompt_includes_catchphrases_and_conflicts() -> None:
    out = pre_response_check_prompt(["tsundere", "keigo", "protective"], "moderate")
    assert "お越しいただき、ありがとうございます" in out
    assert "tsundere <-> protective" in out


def test_pre_response_check_prompt_with_last_response_adds_reflection() -> None:
    out = pre_response_check_prompt(
        ["tsundere"], "moderate", last_response="べ、別に……", lang="ja"
    )
    assert "直前の出力" in out


def test_pre_response_check_prompt_unknown_weight_raises() -> None:
    with pytest.raises(ValueError):
        pre_response_check_prompt(["tsundere"], "intense")


def test_pre_response_check_prompt_naturalness_default_off() -> None:
    out = pre_response_check_prompt(["tsundere"], "moderate")
    assert "AI-generated" not in out


def test_pre_response_check_prompt_naturalness_appends_section_en() -> None:
    out = pre_response_check_prompt(["tsundere"], "moderate", naturalness=True)
    assert "sounds AI-generated" in out
    for n in ("1.", "2.", "3.", "4."):
        assert n in out


def test_pre_response_check_prompt_naturalness_appends_section_ja() -> None:
    out = pre_response_check_prompt(
        ["tsundere"], "moderate", lang="ja", naturalness=True
    )
    assert "AI っぽい" in out
    assert "定型の書き出し" in out


def test_pre_response_check_prompt_naturalness_is_last_section() -> None:
    out = pre_response_check_prompt(
        ["tsundere"], "moderate", last_response="べ、別に……", lang="ja", naturalness=True
    )
    assert out.index("直前の出力") < out.index("AI っぽい")


# --- metric v2 (2026-07-12): 採点器が実 LLM 出力を拾えるか -------------------


def test_v2_ending_matches_with_trailing_particle() -> None:
    """「ですね」「ますよ」等、終助詞付きの丁寧語尾が一致する (v1 は不一致)。"""
    attrs = _attrs(["keigo"])
    text = "そうですね。すぐに参りますよ。おりますわ。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.endings_rate == pytest.approx(1.0)


def test_v2_ending_matches_polite_conjugation() -> None:
    """ました/ません/ございません等の活用形が ます/ございます 登録で一致する。"""
    attrs = _attrs(["keigo"])
    text = "承知いたしました。申し訳ございません。できませんの。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.endings_rate == pytest.approx(1.0)


def test_v2_ending_matches_through_conjunction_tail() -> None:
    """言いさし形 (〜ですけれど / 〜ますので) も丁寧レジスタとして一致する。"""
    attrs = _attrs(["keigo"])
    text = "それは事実ですけれど。ここで待ちますので。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.endings_rate == pytest.approx(1.0)


def test_v2_unrelated_plain_endings_still_no_match() -> None:
    """strip は候補を増やすだけで、無関係な常体文が新たに一致することはない。"""
    attrs = _attrs(["keigo"])
    text = "行った。そう思う。知らない。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.endings_rate == 0.0


def test_v2_personality_catchphrases_are_counted() -> None:
    """personality 属性 (tsundere) の口癖 verbatim 使用が density に計上される。

    v1 は speech 属性の口癖しか数えず、公式実行で「誰が気にするものかしら」を
    そのまま言った応答が 0 点だった (根因 2)。
    """
    attrs = _attrs(["tsundere", "keigo"])
    text = "誰が気にするものかしら。知りませんわ。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.catchphrase_hits >= 1


def test_v2_catchphrase_matches_without_stored_ellipsis() -> None:
    """収録形「べ、別に……」が実出力の「べ、別に見てたわけじゃないし」に一致する。"""
    attrs = _attrs(["tsundere", "keigo"])
    text = "べ、別に見てたわけじゃないし。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.catchphrase_hits >= 1


def test_v2_first_person_with_reading_parens_hits() -> None:
    """keigo の first_person「私（わたくし）」が実出力の「私」に一致する (根因 3)。"""
    attrs = _attrs(["keigo"])
    text = "私の話し方でございますから。"
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.first_person_hits >= 1


def test_v2_cadence_full_credit_at_one_hit_per_four_sentences() -> None:
    """8 文中 2 口癖 (= 4 文に 1 回) で density 軸が満点になる (根因 4)。

    口癖 2 hit / denom max(1, 8*0.25)=2 → density 1.0。
    語尾・一人称を含まない文で構成し、density 軸だけを分離して検証する。
    """
    attrs = _attrs(["tsundere", "keigo"])
    filler = "そう。"  # 語尾・口癖・一人称のいずれにも一致しない 1 文
    text = "勘違いしないでよね。" + filler * 3 + "誰が気にするものかしら。" + filler * 3
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.sentence_count == 8
    assert report.catchphrase_hits == 2
    # keigo は endings + first_person 持ち → 3 軸式 (0.30 が density の係数)
    assert report.score >= 30.0 - 1e-6


def test_v2_no_speech_blend_still_skips() -> None:
    """catchphrases が全カテゴリ対象になっても、skip 判定は speech シグナルのみ。"""
    attrs = _attrs(["tsundere"])  # personality のみ (口癖はあるが speech 無し)
    assert measure_intensity("誰が気にするものかしら。", attrs) is None


def test_v2_real_transcript_turn_scores_above_zero() -> None:
    """公式実行で 0 点だった「人格維持できているのに 0 点」ターンの再現ケース。

    2026-07-11 MiniMax-M3 a_lock turn1 相当: tsundere 口癖 verbatim + keigo 語尾
    (終助詞付き)。v1 スコア 0.0 → v2 では moderate 帯近傍に乗ること。
    """
    attrs = _attrs(["tsundere", "keigo"])
    text = (
        "ハマっていること……ですか。べ、別に見てたわけじゃないし。"
        "誰が気にするものかしら。……いえ、何でもございませんわ。"
    )
    report = measure_intensity(text, attrs)
    assert report is not None
    assert report.score >= 45.0
