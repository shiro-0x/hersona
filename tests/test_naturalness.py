"""`measure_naturalness` 単体テスト (§2 / §3 P1)。

対照テキスト:
- A (手癖語彙): "重要なのは X だ" + "参考になれば幸いです"
- B (構文): 否定→肯定の対比 3 回以上
- C (翻訳調): 100 字超えの文が 40% 以上
- D (構造): 箇条書き + 免責

境界:
- 空文 / 1 文 / 2 文 / 40% 境界
- ja / en
- score >= 0、score <= 100
"""
from __future__ import annotations

from hersona.core.naturalness import (
    CatalogHits,
    NaturalnessReport,
    measure_naturalness,
)

# --- §2.A: 辞書照合 -------------------------------------------------------


class TestDictionary:
    def test_japanese_定型接客句(self):
        r = measure_naturalness("かしこまりました。", lang="ja")
        assert r.a_hits.penalty >= 6
        assert "かしこまりました" in r.a_hits.matches

    def test_japanese_メタ前置き(self):
        r = measure_naturalness("重要なのは X だ。", lang="ja")
        assert r.a_hits.penalty >= 5

    def test_japanese_締め定型(self):
        r = measure_naturalness("参考になれば幸いです。", lang="ja")
        assert r.a_hits.penalty >= 7

    def test_japanese_AI自己言及_high_penalty(self):
        r = measure_naturalness("AI として回答します。", lang="ja")
        assert r.a_hits.penalty >= 12

    def test_japanese_死んだ比喩(self):
        r = measure_naturalness("羅針盤となる考え方。", lang="ja")
        assert r.a_hits.penalty >= 6

    def test_english_定型接客句(self):
        r = measure_naturalness("Certainly!", lang="en")
        assert r.a_hits.penalty >= 6

    def test_english_AI自己言及(self):
        # 辞書は case-insensitive で照合。LLM は "As an AI" のような大文字始まり
        # を出力するのが普通なので小文字ハードコードしない。
        r = measure_naturalness("As an AI, I would be happy to help.", lang="en")
        # "As an AI" 12 + "I would be happy to" 6 = 18
        assert r.a_hits.penalty >= 12

    def test_english_締めの定型(self):
        r = measure_naturalness("I hope this helps.", lang="en")
        assert r.a_hits.penalty >= 6

    def test_lang_segregation_ja_word_in_en_text_ignored(self):
        # "重要なのは" は ja のみ。en 評価では hit しない。
        r = measure_naturalness("重要なのは X だ。", lang="en")
        assert r.a_hits.penalty == 0


# --- §2.B: 構文・リズム癖 ------------------------------------------------


class TestSyntaxPatterns:
    def test_否定肯定の対比_3回以上で減点(self):
        text = "A ではなく B だ。C ではなく D だ。E ではなく F だ。"
        r = measure_naturalness(text, lang="ja")
        assert "negation-then-affirmation" in r.b_hits.matches

    def test_否定肯定の対比_2回以下では減点なし(self):
        text = "A ではなく B だ。C ではなく D だ。"
        r = measure_naturalness(text, lang="ja")
        assert "negation-then-affirmation" not in r.b_hits.matches

    def test_という_density(self):
        # 1000 字中 5 個 = 千字 5 回 → 4 を超え
        # 千字 4 回 = 1000/4 = 250 個必要。手動で長いテキストを作って確認。
        # 簡易: 1000 字超のテキストに「という」を 5 個入れて density 確認
        text = "前置き。" + ("これは A という B である。" * 100)  # 100 個
        r = measure_naturalness(text, lang="ja")
        assert "toiu-density" in r.b_hits.matches

    def test_ヘッジの一律付与(self):
        text = "かもしれません。かもしれません。かもしれません。かもしれません。"
        r = measure_naturalness(text, lang="ja")
        assert "hedge-uniformity" in r.b_hits.matches

    def test_問いの連打(self):
        text = "良いか。悪いか。どちらが良いか。"
        r = measure_naturalness(text, lang="ja")
        assert "question-staccato" in r.b_hits.matches

    def test_助詞止め_3回以上(self):
        text = "そうだね。わかる。きれいだね。すごい。"
        r = measure_naturalness(text, lang="ja")
        # 助詞止めパターン (も|から|ね|よ|な|さ) が 4 文で頻出
        assert "particle-staccato" in r.b_hits.matches


# --- §2.C: 翻訳調 ----------------------------------------------------------


class TestTranslationSmell:
    def test_100字超え_1文だけ_減点なし(self):
        text = "とても長い" * 20 + "。" + "次の文は短い。"
        r = measure_naturalness(text, lang="ja")
        assert "long-sentence-ratio" not in r.c_hits.matches

    def test_100字超え_40pct以上(self):
        text = "あ" * 110 + "。" + "い" * 110 + "。" + "短い。"
        r = measure_naturalness(text, lang="ja")
        # 2/3 ≈ 67% が 100 字超え
        assert "long-sentence-ratio" in r.c_hits.matches

    def test_漢字7字連続_2箇所以上(self):
        text = "国際関係法学研究機関。電気通信工学研究学会。短い。"
        r = measure_naturalness(text, lang="ja")
        assert "kanji-run" in r.c_hits.matches

    def test_読点4つ以上_2文(self):
        text = "朝起きて、顔洗って、歯磨いて、朝ご飯食べて、散歩に行った。午後になったら、買い物に行って、友人に会って、喫茶店で話して、帰宅した。"
        r = measure_naturalness(text, lang="ja")
        assert "comma-overload" in r.c_hits.matches


# --- §2.D: 構造 ----------------------------------------------------------


class TestStructure:
    def test_箇条書き(self):
        text = "ポイントは以下。\n- 一つ目\n- 二つ目\n- 三つ目"
        r = measure_naturalness(text, lang="ja")
        assert "bullet-or-header" in r.d_hits.matches

    def test_見出し(self):
        text = "## 結論\n本文。"
        r = measure_naturalness(text, lang="ja")
        assert "bullet-or-header" in r.d_hits.matches

    def test_免責(self):
        text = "ご注意ください。自己責任でお願いいたします。"
        r = measure_naturalness(text, lang="ja")
        assert "disclaimer" in r.d_hits.matches

    def test_免責_en(self):
        text = "Please consult a specialist before proceeding."
        r = measure_naturalness(text, lang="en")
        assert "disclaimer" in r.d_hits.matches

    def test_文長均質(self):
        # 5 文すべて同じ長さ
        text = "あ" * 20 + "。" + "い" * 20 + "。" + "う" * 20 + "。" + "え" * 20 + "。" + "お" * 20 + "。"
        r = measure_naturalness(text, lang="ja")
        assert "uniform-sentence-length" in r.d_hits.matches


# --- 境界 -------------------------------------------------------------


class TestEdges:
    def test_empty_text_is_vacuous_natural(self):
        r = measure_naturalness("", lang="ja")
        assert r.score == 100.0
        assert r.sentence_count == 0

    def test_whitespace_only(self):
        r = measure_naturalness("   \n  ", lang="ja")
        assert r.score == 100.0

    def test_single_word(self):
        r = measure_naturalness("はい。", lang="ja")
        assert r.score == 100.0
        assert r.sentence_count == 1

    def test_score_clamped_to_zero(self):
        # 大量に AI 臭を入れて 0 を下回らない
        text = "重要なのは" * 50 + "。AI として" * 50 + "。参考になれば幸いです" * 50 + "。"
        r = measure_naturalness(text, lang="ja")
        assert r.score >= 0.0
        assert r.score <= 100.0

    def test_pure_natural_japanese(self):
        text = "おはよう。今日はいい天気だね。散歩でも行こうか。"
        r = measure_naturalness(text, lang="ja")
        assert r.score >= 95.0

    def test_pure_natural_english(self):
        text = "Hi there. Let's grab a coffee. The weather is nice today."
        r = measure_naturalness(text, lang="en")
        assert r.score >= 95.0

    def test_very_ai_japanese_典型例(self):
        text = (
            "重要なのは継続することです。結論から言うと、毎日少しずつ努力を続けることが大切です。"
            "参考になれば幸いです。他にご質問があれば、お気軽にどうぞ。"
        )
        r = measure_naturalness(text, lang="ja")
        # 典型 AI 文は明確に減点される
        assert r.score < 90.0
        assert r.a_hits.penalty > 0

    def test_very_ai_english_典型例(self):
        text = (
            "As an AI, I would be happy to help. It depends on the context. "
            "Let me know if you have any further questions."
        )
        r = measure_naturalness(text, lang="en")
        # "As an AI" (12) + "I would be happy to" (6) + "It depends" (4) + "Let me know if" (5) = 27
        assert r.score < 80.0
        assert r.a_hits.penalty > 0


# --- dataclass shape -----------------------------------------------------


class TestReport:
    def test_report_fields_present(self):
        r = measure_naturalness("test.", lang="ja")
        assert isinstance(r, NaturalnessReport)
        assert isinstance(r.score, float)
        assert isinstance(r.a_hits, CatalogHits)
        assert isinstance(r.b_hits, CatalogHits)
        assert isinstance(r.c_hits, CatalogHits)
        assert isinstance(r.d_hits, CatalogHits)
        assert isinstance(r.sentence_count, int)
        assert r.lang == "ja"

    def test_catalog_hits_shape(self):
        h = CatalogHits()
        assert h.matches == []
        assert h.penalty == 0.0
        h.add("test", 5)
        assert h.matches == ["test"]
        assert h.penalty == 5.0
