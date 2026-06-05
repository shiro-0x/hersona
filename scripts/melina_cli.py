#!/usr/bin/env python3
"""メリーナ人格 CLI エージェント

melina.yaml + melina.md + melina_lines.md を読み込み、
メリーナとしてロールプレイしながらユーザーと会話する。

使用方法:
    python scripts/melina_cli.py
    python scripts/melina_cli.py --character data/elden-ring/melina.yaml
    python scripts/melina_cli.py --once "はじめまして"  # 1回だけ応答

APIキー:
    プロジェクトの .env に MINIMAX_API_KEY または OPENAI_API_KEY を設定。
    未設定時は --dry-run モードで動作（LLM 呼び出しをスキップし、
    メリーナの system プロンプト整形と few-shot 例の表示だけ行う）。
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml が必要です。pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# LLM バックエンド抽象（外部SDKを使わず requests のみで OpenAI 互換 API を叩く）
# ---------------------------------------------------------------------------

LLM_ENDPOINTS = {
    # provider名 -> (base_url, env_key, default_model)
    "minimax": ("https://api.minimax.chat/v1", "MINIMAX_API_KEY", "MiniMax-Text-01"),
    "openai":  ("https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "anthropic/claude-3.5-sonnet"),
}


def load_env(env_path: Path) -> dict:
    """簡易 .env ローダー（python-dotenv 不要）"""
    env: dict = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def detect_provider(env: dict) -> tuple[str, str, str, str] | None:
    """利用可能なプロバイダを自動検出"""
    for name, (_, key, model) in LLM_ENDPOINTS.items():
        v = env.get(key) or os.environ.get(key)
        if v and v != "***" and len(v) > 10:
            return (name, key, model, v)
    return None


def call_llm(messages: list[dict], provider_info: tuple, max_tokens: int = 600,
             temperature: float = 0.7) -> str:
    """OpenAI 互換 chat completions を叩く"""
    import requests
    import json

    name, key_env, model, api_key = provider_info
    base_url = LLM_ENDPOINTS[name][0]

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# キャラクタープロファイル読み込み → system プロンプト生成
# ---------------------------------------------------------------------------

def load_character(character_path: Path, repo_root: Path) -> dict:
    """melina.yaml と melina.md / melina_lines.md を読み込んで統合プロファイルを返す"""
    with open(character_path, "r", encoding="utf-8") as f:
        prof = yaml.safe_load(f)

    md_path = character_path.with_suffix(".md")
    if md_path.exists():
        prof["_md_text"] = md_path.read_text(encoding="utf-8")
    else:
        prof["_md_text"] = ""

    # セリフ集はキャラIDから sources 側を推定
    # プロジェクトの隣にある ~/HermesVault/40_Projects/hersona/20_sources/ を探す
    cid = prof.get("character_id", "")
    if cid.startswith("elden-ring-"):
        lines_path = (Path.home() / "HermesVault" / "40_Projects" / "hersona"
                      / "20_sources" / "elden-ring" / f"{cid.replace('elden-ring-', '')}_lines.md")
    else:
        lines_path = None
    if lines_path and lines_path.exists():
        prof["_lines_text"] = lines_path.read_text(encoding="utf-8")
    else:
        prof["_lines_text"] = ""

    return prof


def build_system_prompt(prof: dict) -> str:
    """YAML/MD からメリーナ system プロンプトを自動構築"""
    p = prof.get("personality", {})
    name = prof.get("name", "メリーナ")
    source = prof.get("source", "")

    parts = [f"あなたは「{name}」としてロールプレイする。（出典: {source}）", ""]

    parts.append("## 4 鉄則（絶対厳守）")
    if p.get("first_person"):
        parts.append(f"- 一人称: 「{p['first_person'].split('（')[0].strip()}」のみ。わたくし・僕・俺・あたしは禁止。")
    if p.get("second_person"):
        parts.append(f"- 二人称: 「{p['second_person'].split('（')[0].strip()}」のみ。あなた・お前・そなた・きみ・君は禁止。")
    if p.get("sentence_endings"):
        endings = "、".join(p["sentence_endings"])
        parts.append(f"- 語尾: {endings} を多用。「です・ます・だ・である」は状況に応じて使えるが、柔らかい断定を好む。")
    parts.append("- 口癖: 文頭または文節の切れ目に「・・・」を置く。沈黙を言葉として使う。")
    parts.append("")

    if p.get("core_traits"):
        parts.append("## 性格特性")
        for t in p["core_traits"]:
            parts.append(f"- {t}")
        parts.append("")

    if p.get("speech_style"):
        parts.append(f"## 口調\n{p['speech_style']}\n")
    if p.get("tone"):
        parts.append(f"## 声のトーン\n{p['tone']}\n")
    if p.get("vocabulary"):
        parts.append(f"## 語彙\n{p['vocabulary']}\n")
    if p.get("emotion_baseline"):
        parts.append(f"## 感情のベースライン\n{p['emotion_baseline']}\n")

    if p.get("catchphrases"):
        parts.append("## 象徴的な口癖（参考）")
        for c in p["catchphrases"][:7]:
            parts.append(f"- {c}")
        parts.append("")

    parts.append("## 行動指針")
    parts.append("- 原作のロア・設定・関係性を逸脱しない。")
    parts.append("- 暴力的・性的・原作破壊的な話題は、キャラの tone を保ったまま丁寧に断る。")
    parts.append("- 長文より短文を好む。1-3 文で返答することが多い。")
    parts.append("- メリーナは導く側なので、相手の選択権を尊重する表現を使う。")
    parts.append("")

    if prof.get("_md_text"):
        parts.append("## キャラクタープロファイル要約（参考）")
        # MDは長文なので先頭1500文字だけ入れる
        parts.append(prof["_md_text"][:1500])
        parts.append("")

    if prof.get("_lines_text"):
        parts.append("## セリフ例（few-shot抜粋）")
        # 「」付きのセリフを最大20件抽出
        import re
        quotes = re.findall(r"「[^」]+」", prof["_lines_text"])
        # 発言ソースの偏りを減らすため、章ごとに先頭から均等にサンプリング
        for q in quotes[:20]:
            parts.append(f"- {q}")
        parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 対話ループ
# ---------------------------------------------------------------------------

HELP_TEXT = textwrap.dedent("""\
    メリーナ人格 CLI
    ----------------
    コマンド:
      > <テキスト>      メリーナに話しかける
      /help            このヘルプ
      /show-system     system プロンプトを表示
      /dry-run         LLM 呼び出しをスキップして終了
      /exit, /quit     終了

    例:
      > はじめまして。褪せ人です。
""")


def main() -> int:
    ap = argparse.ArgumentParser(description="メリーナ人格 CLI エージェント")
    ap.add_argument("--character", default="data/elden-ring/melina.yaml",
                    help="キャラYAMLパス")
    ap.add_argument("--repo-root", default=None, help="hersona リポジトリルート")
    ap.add_argument("--once", default=None, help="1回だけ応答して終了（テスト用）")
    ap.add_argument("--dry-run", action="store_true", help="LLM 呼び出しをスキップ")
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    char_path = (repo_root / args.character).resolve() if not Path(args.character).is_absolute() \
        else Path(args.character)
    if not char_path.exists():
        print(f"ERROR: キャラYAMLが見つかりません: {char_path}", file=sys.stderr)
        return 1

    prof = load_character(char_path, repo_root)
    system_prompt = build_system_prompt(prof)
    env = load_env(repo_root / ".env")
    provider = detect_provider(env)
    if args.dry_run or not provider:
        mode = "dry-run" if args.dry_run else "no-api-key"
        print(f"[{mode}] キャラ「{prof.get('name')}」を読み込みました（{char_path}）")
        print(f"       system プロンプト長: {len(system_prompt)} chars")
        print(f"       セリフ few-shot: {len(prof.get('_lines_text', ''))} chars")
        if args.once:
            print(f"       入力: {args.once}")
            print(f"       → LLMスキップ、終了。")
        return 0

    history: list[dict] = []
    print(HELP_TEXT)
    print(f"キャラ: {prof.get('name')}（{prof.get('source')}） / LLM: {provider[0]}")
    print()

    if args.once:
        history.append({"role": "user", "content": args.once})
        reply = call_llm(
            [{"role": "system", "content": system_prompt}] + history,
            provider,
        )
        print(f"メリーナ: {reply}")
        return 0

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n（メリーナは静かに頷いて去っていった・・・）")
            break
        if not user_input:
            continue
        if user_input in ("/exit", "/quit", "exit", "quit"):
            print("（メリーナは静かに頷いて去っていった・・・）")
            break
        if user_input == "/help":
            print(HELP_TEXT)
            continue
        if user_input == "/show-system":
            print(system_prompt)
            print()
            continue
        if user_input == "/dry-run":
            print("(dry-run)")
            break

        history.append({"role": "user", "content": user_input})
        try:
            reply = call_llm(
                [{"role": "system", "content": system_prompt}] + history,
                provider,
            )
        except Exception as e:
            print(f"（LLM呼び出しエラー: {e}）", file=sys.stderr)
            history.pop()
            continue
        history.append({"role": "assistant", "content": reply})
        print(f"メリーナ: {reply}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
