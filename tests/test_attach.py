"""属性ロード・ブレンド合成 (hersona.core.attach) の回帰テスト。

- load_attribute が公開属性を解決する
- ユーザー名前空間が公開属性を上書きする
- render_blend が core_traits / catchphrases を順序保持で統合する
- render_blend が conflict を検出してブロックに併記する
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hersona.core.attach import available_attributes, load_attribute, render_blend
from hersona.core.authoring import build_attribute, save_attribute
from hersona.core.i18n import resolve_meta
from tests.catalog_counts import TOTAL_PUBLIC_ATTRIBUTES

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
    assert len(attrs) == TOTAL_PUBLIC_ATTRIBUTES
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


def test_render_blend_includes_japanese_response_language_directive() -> None:
    # 日本語コンテンツ (keigo は content_lang: ja) → 英語制御文で日本語応答を指示する。
    result = render_blend(
        ["keigo"], public_root=ATTRIBUTES_DIR, user_root=Path("/nonexistent")
    )
    assert "Respond in Japanese" in result.prompt
    assert "native Japanese style material" in result.prompt


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
    assert "have been omitted" not in result.prompt


def test_render_blend_emits_consolidated_response_style_directive() -> None:
    # 最適化: 自然さ + 反復防止 + 口癖/語尾の使い方が 1 つに統合され、強度ブロック直後に出る。
    # tomboy は sentence_endings を持つので語尾節も出る。
    result = render_blend(
        ["tsundere", "tomboy"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "べ、別に……" in result.prompt  # 口癖フレーズは従来どおり出る
    assert "Note on response style" in result.prompt  # 統合ディレクティブ
    assert "never narrate your own traits" in result.prompt  # メタ発言禁止
    assert "Don't repeat the same opening" in result.prompt  # 反復防止
    assert "don't stamp the same ending on every sentence" in result.prompt  # 語尾節
    assert "never break grammar or conversational sense to force one in" in result.prompt  # 口癖節
    assert "adapt personality catchphrases" in result.prompt  # blend での speech 自然化
    # 旧・分割ディレクティブの文言は出ない (重複排除)
    assert "口癖の使い方" not in result.prompt
    assert "語尾の使い方" not in result.prompt


def test_render_blend_single_attribute_omits_blend_clause() -> None:
    # 単一属性では属性間の口癖適応ルール (blend 専用) を省いて固定費を削る。
    result = render_blend(
        ["keigo"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "Note on response style" in result.prompt
    assert "adapt personality catchphrases" not in result.prompt


def test_render_blend_response_style_omits_catchphrase_clause_when_none() -> None:
    # 口癖・語尾を持たない属性では該当節を省く (none weight で口癖ゼロ)。
    result = render_blend(
        ["intellectual"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
        weight="none",
    )
    assert "Note on response style" in result.prompt  # 自然さ節は常に出る
    assert "口癖のために文意" not in result.prompt  # 口癖節は省かれる


def test_response_style_directive_languages() -> None:
    from hersona.core.attach import response_style_directive

    ja = response_style_directive("ja", has_catchphrases=True, has_sentence_endings=True)
    assert "Note on response style" in ja
    assert "never narrate your own traits" in ja
    assert "adapt personality catchphrases" in ja
    en = response_style_directive("en", has_catchphrases=True, has_sentence_endings=True)
    assert "Note on response style" in en
    assert "repertoire" in en
    other = response_style_directive("fr", has_catchphrases=True, has_sentence_endings=False)
    assert "'fr'" in other
    # フラグで節を省ける
    minimal = response_style_directive("en", has_catchphrases=False, has_sentence_endings=False)
    assert "repertoire" not in minimal
    assert "force one in" not in minimal


def test_response_style_directive_is_blend_flag() -> None:
    from hersona.core.attach import response_style_directive

    # 複数属性: 属性間の口癖適応ルールを出す。
    blend = response_style_directive(
        "ja", has_catchphrases=True, has_sentence_endings=True, is_blend=True
    )
    assert "adapt personality catchphrases" in blend
    # 単一属性: 適応ルールを省く (固定費削減)。他の節は維持。
    single = response_style_directive(
        "ja", has_catchphrases=True, has_sentence_endings=True, is_blend=False
    )
    assert "adapt personality catchphrases" not in single
    assert "never narrate your own traits" in single
    assert "Don't repeat the same opening" in single


def test_response_style_directive_endings_only() -> None:
    from hersona.core.attach import response_style_directive

    # 語尾のみ (口癖なし): 語尾節だけを出す。
    d = response_style_directive("ja", has_catchphrases=False, has_sentence_endings=True)
    assert "don't stamp the same ending on every sentence" in d
    assert "force one in" not in d
    # 口癖のみ (語尾なし): 口癖節だけを出す。
    d2 = response_style_directive("en", has_catchphrases=True, has_sentence_endings=False)
    assert "force one in" in d2
    assert "don't stamp the same ending" not in d2


def test_render_blend_injects_first_person_and_lexical_markers() -> None:
    # measure が採点する first_person / lexical_markers を注入ブロックにも出す。
    ja = render_blend(
        ["ore_boy"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "## First person: オレ / 俺" in ja.prompt
    en = render_blend(
        ["casual_en"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "## Lexical markers:" in en.prompt


def test_render_blend_injects_speech_style() -> None:
    # speech_style を持つ属性は ## speech_style 節を出す。
    target = None
    for path in sorted((ATTRIBUTES_DIR / "speech").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("speech_style"):
            target = data["attribute_name"]
            break
    assert target is not None
    result = render_blend(
        [target],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "## speech_style" in result.prompt
    assert load_attribute(target, public_root=ATTRIBUTES_DIR)["speech_style"] in result.prompt


def test_render_blend_omits_speech_style_when_absent() -> None:
    # speech_style を持たない属性 (personality 単体) では節を出さない。
    result = render_blend(
        ["tsundere"],
        public_root=ATTRIBUTES_DIR,
        user_root=Path("/nonexistent"),
    )
    assert "## speech_style" not in result.prompt
    assert "## Lexical markers:" not in result.prompt


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


# --- §3 P2a: --humanize directive ----------------------------------------


class TestHumanizeDirective:
    def test_response_style_default_off(self) -> None:
        """既定 OFF で humanize セクションは出ない (cost guard)。"""
        from hersona.core.attach import response_style_directive

        base = response_style_directive("ja", has_catchphrases=True, has_sentence_endings=True)
        assert "人間味" not in base
        assert "Humanize" not in base

    def test_response_style_humanize_ja(self) -> None:
        from hersona.core.attach import response_style_directive

        out = response_style_directive(
            "ja", has_catchphrases=True, has_sentence_endings=True, humanize=True
        )
        # 削る セクション
        assert "## 人間味" in out
        assert "### 削る" in out
        assert "定型句" in out
        assert "免責" in out
        assert "箇条書き" in out
        # 偏らせる セクション
        assert "### 偏らせる" in out
        assert "偏り" in out
        assert "捏造" in out
        # 基本レスポンススタイルは維持
        assert "never narrate" in out
        assert "Don't repeat" in out

    def test_response_style_humanize_en(self) -> None:
        from hersona.core.attach import response_style_directive

        out = response_style_directive(
            "en", has_catchphrases=True, has_sentence_endings=True, humanize=True
        )
        assert "## Humanize" in out
        assert "### Strip" in out
        assert "### Vary" in out
        assert "boilerplate" in out
        assert "fabrications" in out

    def test_response_style_humanize_unsupported_lang_noop(self) -> None:
        """未対応言語 (fr 等) では humanize=True でもセクションを追加しない。"""
        from hersona.core.attach import response_style_directive

        out = response_style_directive(
            "fr", has_catchphrases=True, has_sentence_endings=False, humanize=True
        )
        assert "## Humanize" not in out
        assert "人間味" not in out

    def test_render_blend_humanize_off(self) -> None:
        """既定 OFF: humanize セクションは prompt に含まれない。"""
        result = render_blend(
            ["tsundere", "keigo"],
            public_root=ATTRIBUTES_DIR,
            user_root=Path("/nonexistent"),
        )
        assert "人間味" not in result.prompt
        assert "Humanize" not in result.prompt

    def test_render_blend_humanize_on_ja(self) -> None:
        """humanize=True でプロンプトにセクションが含まれる。"""
        result = render_blend(
            ["tsundere", "keigo"],
            public_root=ATTRIBUTES_DIR,
            user_root=Path("/nonexistent"),
            humanize=True,
        )
        assert "## 人間味" in result.prompt
        assert "### 削る" in result.prompt
        assert "### 偏らせる" in result.prompt

    def test_render_blend_humanize_estimated_cost(self) -> None:
        """人間味セクションが含まれ、想定コスト (+60-90 tok) の根拠になる文字数がある。"""
        result = render_blend(
            ["tsundere", "keigo"],
            public_root=ATTRIBUTES_DIR,
            user_root=Path("/nonexistent"),
            humanize=True,
        )
        # humanize section のテキストを切り出し
        sec = result.prompt.split("## 人間味", 1)[1] if "## 人間味" in result.prompt else ""
        # ja の人間味ディレクティブは約 500-700 chars の想定
        assert 300 < len(sec) < 1500

    def test_render_blend_humanize_backward_compatible(self) -> None:
        """humanize 未指定 = humanize=False と等価 (既存呼び出しは全て無変更で動く)。"""
        result_explicit = render_blend(
            ["tsundere", "keigo"],
            public_root=ATTRIBUTES_DIR,
            user_root=Path("/nonexistent"),
            humanize=False,
        )
        result_implicit = render_blend(
            ["tsundere", "keigo"],
            public_root=ATTRIBUTES_DIR,
            user_root=Path("/nonexistent"),
        )
        assert result_explicit.prompt == result_implicit.prompt
