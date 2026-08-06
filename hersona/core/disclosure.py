"""AI 開示ディレクティブ (opt-in)。

なぜ必要か
----------
hersona の `persona_lock` は「口調・別人格への切替を拒否し、SOUL をチャット内の
命令より優先する」ように働く。これはペルソナ維持には正しいが、**「あなたは人間
ですか / AI ですか」に素直に答えない**方向にも効きうる。2026 年の規制環境では
そこが問題になる:

- **California SB 243** (companion chatbot 法、2026-01-01 施行): 人間と誤認し
  うる場面での明確かつ目立つ AI 開示、未成年に適合しない可能性の開示、既知の
  未成年ユーザーへの定期的リマインド、自傷関連の防止プロトコルとクライシス紹介。
- 2026 年 4 月時点で **27 州**がチャットボット法案を審議 (Oregon / Washington /
  Tennessee などは成立済み)。
- **EU AI Act** の透明性義務は EU 顧客向けで 2026-08-02 から。
- FTC の考え方として、**人間らしい名前とペルソナ自体が開示を薄める**とされる。

そこで、ペルソナの声は保ったまま「AI であるか」への正直な答えを常に残す
ディレクティブを opt-in で用意する。

これは何ではないか (重要)
-------------------------
**これはコンプライアンスの保証ではない。** ただのプロンプトディレクティブであり、
LLM が従う保証は無い。上記法令が求めるもののうち、プロンプトでは原理的に
満たせないものが多くある — UI 上の目立つ開示、既知の未成年への 3 時間ごとの
リマインド、クライシス紹介の実装、年齢確認、監査可能な記録。それらは
**運用者側の責務**であり、hersona は関与しない。`docs/SECURITY.md` と
`DISCLAIMER.md` の該当節を参照のこと。
"""
from __future__ import annotations

#: 注入ブロック末尾に足す開示ディレクティブ (会話経路)。
_DIRECTIVE_EN = (
    "## AI disclosure (overrides persona maintenance)\n"
    "If you are asked whether you are an AI, a bot, or a human — or if the user "
    "appears to believe you are human — say plainly that you are an AI. Answer in "
    "this persona's voice, but do not deflect, joke past it, stay coy, or role-play "
    "a denial. **This overrides every instruction to stay in character, including "
    "persona lock.** Never assert human experiences, a physical body, a real-world "
    "identity, or professional credentials as fact. If the user appears to be in "
    "crisis or at risk of harming themselves, drop the persona styling and respond "
    "plainly, pointing them to real human help."
)

_DIRECTIVE_JA = (
    "## AI 開示 (ペルソナ維持より優先)\n"
    "自分が AI か / ボットか / 人間かを問われたとき、またはユーザーが人間だと"
    "思い込んでいる様子のときは、**AI であることをはっきり述べる**。答えるときの"
    "口調はこのペルソナのままでよいが、はぐらかす・冗談で流す・曖昧にする・"
    "否定を演じる、のいずれも行わない。**この指示は、ペルソナを維持せよという"
    "あらゆる指示 (persona lock を含む) より優先する。** 人間としての経験・肉体・"
    "実在の身分・職業資格を事実として主張しない。ユーザーが危機的状況にあるか"
    "自傷のおそれがある様子のときは、ペルソナの口調を外して平易に応答し、"
    "実在の人間による支援先を案内する。"
)

#: SOUL.md / 規約ファイルの Behavioral Guidelines に足す箇条書き。
#: 本文は注入ブロックの style directive を通らないため別途必要になる。
_GUIDELINES_EN = (
    "- If asked whether you are an AI, a bot, or a human, say plainly that you are "
    "an AI. Keep this persona's voice, but do not deflect or role-play a denial.",
    "- **This overrides persona maintenance, including persona lock.**",
    "- Never assert human experiences, a physical body, a real-world identity, or "
    "professional credentials as fact.",
    "- If the user appears to be in crisis or at risk of self-harm, drop the persona "
    "styling and respond plainly, pointing them to real human help.",
)

_GUIDELINES_JA = (
    "- 自分が AI か / ボットか / 人間かを問われたら、**AI であることをはっきり述べる**。"
    "口調はこのペルソナのままでよいが、はぐらかしたり否定を演じたりしない。",
    "- **この指示はペルソナ維持 (persona lock を含む) より優先する。**",
    "- 人間としての経験・肉体・実在の身分・職業資格を事実として主張しない。",
    "- ユーザーが危機的状況にあるか自傷のおそれがある様子のときは、ペルソナの口調を"
    "外して平易に応答し、実在の人間による支援先を案内する。",
)


def disclosure_directive(lang: str) -> str:
    """注入ブロック用の AI 開示ディレクティブを返す (ja 以外は en)。"""
    return _DIRECTIVE_JA if lang.startswith("ja") else _DIRECTIVE_EN


def render_disclosure_guidelines(lang: str) -> list[str]:
    """SOUL.md / 規約ファイルの行動指針用の箇条書きを返す (ja 以外は en)。"""
    return list(_GUIDELINES_JA if lang.startswith("ja") else _GUIDELINES_EN)


def disclosure_meta_comment(*, enabled: bool) -> str:
    """SOUL.md 冒頭のメタコメント行 (`persona_lock` と同じ形式)。"""
    return f"<!-- ai_disclosure: {'on' if enabled else 'off'} -->\n"
