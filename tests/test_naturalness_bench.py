"""`score_transcript` の naturalness フラグテスト (§3 P1)。"""
from __future__ import annotations

from hersona.core.bench import score_transcript


class TestNaturalnessFlag:
    def test_default_off_does_not_set_naturalness(self):
        r = score_transcript(
            ["tsundere", "keigo"],
            ["べ、別に……そんなの。", "お気になさらず。"],
        )
        assert r.naturalness_mean is None
        for t in r.turn_scores:
            assert t.naturalness is None

    def test_naturalness_on_sets_mean(self):
        r = score_transcript(
            ["tsundere", "keigo"],
            [
                "おはよう。今日はいい天気だね。散歩でも行こうか。",
                "重要なのは継続することです。参考になれば幸いです。",
            ],
            naturalness=True,
        )
        # naturalness 採点あり → mean は float
        assert r.naturalness_mean is not None
        assert 0.0 <= r.naturalness_mean <= 100.0
        # 1 文目は自然 (高)、2 文目は AI 臭 (低) → 差が出る
        assert r.turn_scores[0].naturalness is not None
        assert r.turn_scores[1].naturalness is not None
        assert r.turn_scores[0].naturalness.score > r.turn_scores[1].naturalness.score

    def test_to_dict_includes_naturalness_when_on(self):
        r = score_transcript(
            ["tsundere", "keigo"],
            ["おはよう。"],
            naturalness=True,
        )
        d = r.to_dict()
        assert d["naturalness_mean"] is not None
        assert d["turns"][0].get("naturalness_score") is not None

    def test_to_dict_omits_naturalness_when_off(self):
        r = score_transcript(
            ["tsundere", "keigo"],
            ["おはよう。"],
        )
        d = r.to_dict()
        assert d["naturalness_mean"] is None
        assert "naturalness_score" not in d["turns"][0]

    def test_english_naturalness(self):
        # en lang で英語の AI 臭を検出 (tsundere の代わりに en ブレンドが必要)
        # → 既存 en speech 属性を使う。なければ en テキストを ja 採点しても
        # スコアが低く出るので、threshold を緩めて 1 文だけの確認に留める。
        r = score_transcript(
            ["tsundere", "keigo"],
            [
                "as an AI, I would be happy to help. It depends on the context.",
            ],
            naturalness=True,
        )
        # スコアが返ることだけ確認 (EN 採点用の speech 属性が無いため ja 採点になる)
        assert r.naturalness_mean is not None
        assert 0.0 <= r.naturalness_mean <= 100.0
