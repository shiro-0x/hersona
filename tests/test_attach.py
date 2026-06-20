"""属性ロード・ブレンド合成 (hersona.core.attach) の回帰テスト。

- load_attribute が公開属性を解決する
- ユーザー名前空間が公開属性を上書きする
- render_blend が core_traits / catchphrases を順序保持で統合する
- render_blend が conflict を検出してブロックに併記する
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.authoring import build_attribute, save_attribute
from hersona.core.i18n import resolve_meta

REPO_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES_DIR = REPO_ROOT / "attributes"


def test_load_public_attribute() -> None:
    data = load_attribute("tsundere", public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
    assert data["attribute_name"] == "tsundere"
    assert data["attribute_category"] == "personality"


def test_load_unknown_raises() -> None:
    with pytest.raises(KeyError):
        load_attribute("nope", public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))


def test_user_namespace_overrides_public(tmp_path: Path) -> None:
    # tsundere を user 名前空間で上書き保存
    override = build_attribute(
        attribute_category="personality",
        attribute_name="tsundere",
        display_name_ja="独自ツンデレ",
        display_name_en="My Tsundere",
        weight_dimension="strong",
        description_ja="上書き版",
        description_en="overridden",
        examples=["ex"],
    )
    save_attribute(override, user_root=tmp_path)
    data = load_attribute("tsundere", public_root=ATTRIBUTES_DIR, user_root=tmp_path)
    assert resolve_meta(data, "display_name", "ja") == "独自ツンデレ"  # user 優先


def test_available_attributes_counts_public() -> None:
    attrs = available_attributes(public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
    assert len(attrs) == 75
    assert attrs["tsundere"]["source"] == "public"


def test_render_blend_merges_fields() -> None:
    result = render_blend(
        ["tsundere", "keigo"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert result.names == ["tsundere", "keigo"]
    assert "core_traits" in result.prompt
    assert "べ、別に……" in result.prompt  # tsundere の catchphrase
    assert result.conflicts == []


def test_render_blend_includes_japanese_language_directive() -> None:
    # 日本語コンテンツ (keigo は content_lang: ja) → 日本語応答の指示行が入る。
    result = render_blend(
        ["keigo"], public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent")
    )
    assert "応答は日本語で行う" in result.prompt


def test_render_blend_english_persona_resolves_native_content() -> None:
    # W1 Step 2: 英語 speech + ja personality (tsundere は content_i18n.en を持つ)。
    # 注入は英語のネイティブ・コンテンツに解決され、日本語は出ず、除外指示も不要。
    result = render_blend(
        ["southern_us_en", "tsundere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "Respond in English" in result.prompt
    assert "Y'all come back now." in result.prompt  # 英語 speech の口癖
    assert "Don't get the wrong idea!" in result.prompt  # tsundere の英語口癖
    assert "Can't be honest" in result.prompt  # tsundere の英語 core_traits
    assert "べ、別に……" not in result.prompt  # 日本語 personality 口癖は出ない
    assert "generated natively in English" not in result.prompt  # 全て解決済→指示不要


def test_render_blend_directive_when_attr_lacks_native_content(tmp_path: Path) -> None:
    # en コンテンツを持たない属性を英語ペルソナにブレンドすると、
    # その ja 口癖は除外され、ネイティブ生成の指示行が出る (W1 Step 1 のフォールバック)。
    cat = tmp_path / "personality"
    cat.mkdir(parents=True)
    (cat / "noenc.yaml").write_text(
        "attribute_category: personality\n"
        "attribute_name: noenc\n"
        "display_name: NoEn\n"
        "weight_dimension: moderate\n"
        "description: test\n"
        "examples:\n- ex\n"
        "catchphrases:\n- 日本語の口癖だよ\n",
        encoding="utf-8",
    )
    result = render_blend(
        ["british_en", "noenc"],
        public_root=ATTRIBUTES_DIR,
        user_root=tmp_path,
    )
    assert "日本語の口癖だよ" not in result.prompt  # 非ネイティブ ja 口癖は除外
    assert "generated natively in English" in result.prompt  # 生成指示が出る


def test_render_blend_japanese_persona_keeps_catchphrases_no_directive() -> None:
    # 純 ja ペルソナは従来どおり。日本語口癖は残り、除外指示は出ない。
    result = render_blend(
        ["tsundere", "keigo"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "べ、別に……" in result.prompt
    assert "natively in English" not in result.prompt
    assert "除外した" not in result.prompt


def test_render_blend_emits_consolidated_response_style_directive() -> None:
    # 最適化: 自然さ + 反復防止 + 口癖/語尾の使い方が 1 つに統合され、強度ブロック直後に出る。
    result = render_blend(
        ["tsundere", "keigo"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "べ、別に……" in result.prompt  # 口癖フレーズは従来どおり出る
    assert "自然さ最優先" in result.prompt  # 統合ディレクティブ
    assert "前置きをしない" in result.prompt  # メタ発言禁止
    assert "繰り返さず" in result.prompt  # 反復防止
    assert "全文に同じ語尾を貼らない" in result.prompt  # 語尾節 (語尾あり属性)
    assert "口癖のために文意・文法を壊さない" in result.prompt  # 口癖節 (口癖あり)
    # 旧・分割ディレクティブの文言は出ない (重複排除)
    assert "口癖の使い方" not in result.prompt
    assert "語尾の使い方" not in result.prompt


def test_render_blend_response_style_omits_catchphrase_clause_when_none() -> None:
    # 口癖・語尾を持たない属性では該当節を省く (none weight で口癖ゼロ)。
    result = render_blend(
        ["intellectual"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
        weight="none",
    )
    assert "自然さ最優先" in result.prompt  # 自然さ節は常に出る
    assert "口癖のために文意" not in result.prompt  # 口癖節は省かれる


def test_response_style_directive_languages() -> None:
    from hersona.core.attach import response_style_directive

    ja = response_style_directive("ja", has_catchphrases=True, has_sentence_endings=True)
    assert "自然さ最優先" in ja
    assert "前置きをしない" in ja
    en = response_style_directive("en", has_catchphrases=True, has_sentence_endings=True)
    assert "Note on response style" in en
    assert "repertoire" in en
    other = response_style_directive("fr", has_catchphrases=True, has_sentence_endings=False)
    assert "'fr'" in other
    # フラグで節を省ける
    minimal = response_style_directive("en", has_catchphrases=False, has_sentence_endings=False)
    assert "repertoire" not in minimal
    assert "force a catchphrase" not in minimal


def test_render_blend_catchphrase_trigger_annotation() -> None:
    # B: when が付いた口癖は「phrase — when」形式でレンダリングされる。
    result = render_blend(
        ["tsundere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    # tsundere の最初の口癖は when 付き
    assert "べ、別に…… — 好意・感謝・心配を向けられ" in result.prompt
    # when なし口癖（……バカ）はダッシュなしで出る (strong で全件確認)
    result_strong = render_blend(
        ["tsundere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
        weight="strong",
    )
    assert "- ……バカ\n" in result_strong.prompt or result_strong.prompt.endswith("- ……バカ")


def test_render_blend_catchphrase_trigger_yandere() -> None:
    # B: yandere の全口癖に when が付いており、それが反映される。
    result = render_blend(
        ["yandere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "ずっと一緒だよ — 別れを告げられるか" in result.prompt
    assert "……今、誰のこと考えてた？ — 相手が別の人" in result.prompt


def test_render_blend_english_response_style_directive() -> None:
    # en コンテンツでは英語の統合応答スタイルルールが入る。
    result = render_blend(
        ["british_en"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "Note on response style" in result.prompt


def test_render_blend_detects_conflict() -> None:
    result = render_blend(
        ["genki", "kuudere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert ("genki", "kuudere") in result.conflicts
    assert "conflict" in result.prompt.lower()


def test_render_blend_empty_raises() -> None:
    with pytest.raises(ValueError):
        render_blend([], public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent"))
