#!/usr/bin/env python3
"""hersona 人格アタッチメント CLI

YAML/MD から persona_attach_prompt フィールドを抽出し、表示・チェック・登録手順案内、
および example_dialogues を attach_prompt に統合した完全なシステムプロンプト生成を行う。

使用方法:
    python scripts/persona_attach.py --list
    python scripts/persona_attach.py --show melina
    python scripts/persona_attach.py --check melina --input sample.txt
    python scripts/persona_attach.py --register melina            # 登録手順の表示のみ（config.yaml 不変更）
    python scripts/persona_attach.py --register melina --write    # config.yaml へ実際に書き込む（自動バックアップあり）
    python scripts/persona_attach.py --register melina --write --dry-run  # 書き込み内容の確認のみ
    python scripts/persona_attach.py --detach melina
    python scripts/persona_attach.py --attach melina   # attach_prompt + example_dialogues 統合
    python scripts/persona_attach.py --check melina --input sample.txt --side user  # user 側のみ評価
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
    import jsonschema
except ImportError:
    print("ERROR: pyyaml / jsonschema が必要です", file=sys.stderr)
    sys.exit(1)


SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "persona_attach.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def find_all_profiles(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "data").rglob("*.yaml"))


def load_attach_prompts(repo_root: Path, schema: dict) -> list[dict]:
    prompts: list[dict] = []
    for yml in find_all_profiles(repo_root):
        try:
            with open(yml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            continue
        if not data or "persona_attach_prompt" not in data:
            continue
        ap = data["persona_attach_prompt"]
        try:
            jsonschema.validate(ap, schema)
        except jsonschema.ValidationError as e:
            print(f"WARNING: {yml} の persona_attach_prompt がスキーマ違反: {e.message}", file=sys.stderr)
            continue
        ap["_source_path"] = str(yml.relative_to(repo_root))
        ap["_character_name"] = data.get("name", ap.get("name", "?"))
        prompts.append(ap)
    return prompts


def cmd_list(prompts: list[dict]) -> int:
    if not prompts:
        print("persona_attach_prompt を持つキャラが data/ 配下に見つかりません")
        return 1
    print(f"利用可能な人格プリセット: {len(prompts)}件")
    print()
    for ap in prompts:
        print(f"  - {ap['register_call']:20s} {ap['_character_name']:20s} "
              f"intensity={ap.get('intensity', 7):2d} style={ap.get('attach_style','strict')}")
    return 0


def cmd_show(prompts: list[dict], register_call: str) -> int:
    for ap in prompts:
        if ap["register_call"] == register_call:
            print(f"=== {ap['name']} (persona_attach_prompt v{ap['version']}) ===")
            print(f"character_id:    {ap['character_id']}")
            print(f"register_call:   {ap['register_call']}")
            print(f"attach_style:    {ap.get('attach_style', 'strict')}")
            print(f"user_role_label: {ap.get('user_role_label', '?')}")
            print(f"intensity:       {ap.get('intensity', 7)}/10")
            print(f"detach_command:  {ap['detach_command']}")
            print(f"source:          {ap['_source_path']}")
            print()
            print("--- user_role_acknowledgement ---")
            print(ap.get("user_role_acknowledgement", "(なし)").strip())
            print()
            print("--- attach_prompt (LLM に注入される本文) ---")
            print(ap["attach_prompt"].strip())
            print()
            print("--- forbidden_words ---")
            for w in ap["forbidden_words"]:
                print(f"  - {w}")
            print()
            print("--- required_words ---")
            for w in ap["required_words"]:
                print(f"  - {w}")
            return 0
    print(f"ERROR: register_call='{register_call}' が見つかりません", file=sys.stderr)
    return 1


def extract_assistant_only(text: str) -> str:
    """入力テキストから assistant 側の発話のみを抽出する。

    対応フォーマット:
      - 「assistant: ...」 / 「A: ...」 / 「> ...」で始まる行
      - 上記マーカーがない場合は入力全体を assistant 側とみなす（後方互換）

    判定: 行頭のラベルを検出して、user 発話を除外する。
    """
    import re as _re

    out_lines: list[str] = []
    in_assistant = False
    for line in text.splitlines():
        stripped = line.lstrip()
        # user 側の判定
        if _re.match(r"^(user|u|User|USER)\s*[:：]\s*", stripped):
            in_assistant = False
            continue
        if _re.match(r"^(situation|Situation|SITUATION)\s*[:：]\s*", stripped):
            in_assistant = False
            continue
        # assistant 側の判定
        if _re.match(r"^(assistant|a|Assistant|ASSISTANT|response|Response)\s*[:：]\s*", stripped):
            in_assistant = True
            out_lines.append(_re.sub(r"^(assistant|a|Assistant|ASSISTANT|response|Response)\s*[:：]\s*", "", stripped))
            continue
        # クォート行「>」は assistant の継続とみなす
        if stripped.startswith(">"):
            in_assistant = True
            out_lines.append(stripped.lstrip("> ").rstrip())
            continue
        if in_assistant and stripped:
            out_lines.append(stripped.rstrip())
    return "\n".join(out_lines).strip()


def cmd_attach(prompts: list[dict], register_call: str) -> int:
    """attach_prompt + example_dialogues を統合したシステムプロンプトを生成・表示する。

    example_dialogues の各ターンは「## 応答例」セクション配下に user/assistant ペアで結合される。
    """
    for ap in prompts:
        if ap["register_call"] != register_call:
            continue
        out: list[str] = []
        out.append(ap["attach_prompt"].strip())
        examples = ap.get("example_dialogues") or []
        if examples:
            out.append("")
            out.append("## 応答例")
            for i, ex in enumerate(examples, 1):
                ctx = ex.get("context", "")
                if ctx:
                    out.append(f"\n### 例 {i}（{ctx}）")
                else:
                    out.append(f"\n### 例 {i}")
                out.append(f"user: {ex['user']}")
                out.append(f"assistant: {ex['assistant']}")
        out.append("")
        out.append(f"## 解除")
        out.append(f"人格を解除するには: {ap['detach_command']}")
        print("\n".join(out))
        return 0
    print(f"ERROR: register_call='{register_call}' が見つかりません", file=sys.stderr)
    return 1


def cmd_check(prompts: list[dict], register_call: str, input_path: Path, side: str = "assistant") -> int:
    for ap in prompts:
        if ap["register_call"] != register_call:
            continue
        raw_text = input_path.read_text(encoding="utf-8")
        if side == "assistant":
            text = extract_assistant_only(raw_text)
            if not text:
                print(f"WARNING: --side assistant 指定だが assistant 側の発話を抽出できなかった。入力をそのまま評価する。", file=sys.stderr)
                text = raw_text
        elif side == "user":
            # user 側を抽出（逆方向）
            user_lines: list[str] = []
            is_user = False
            for line in raw_text.splitlines():
                stripped = line.lstrip()
                if re.match(r"^(user|u|User|USER)\s*[:：]\s*", stripped):
                    is_user = True
                    user_lines.append(re.sub(r"^(user|u|User|USER)\s*[:：]\s*", "", stripped))
                    continue
                if re.match(r"^(assistant|a|Assistant|ASSISTANT)\s*[:：]\s*", stripped):
                    is_user = False
                    continue
                if is_user and stripped:
                    user_lines.append(stripped.rstrip())
            text = "\n".join(user_lines).strip() or raw_text
        elif side == "all":
            text = raw_text
        else:
            print(f"ERROR: --side は user / assistant / all のいずれか", file=sys.stderr)
            return 1

        score = 100
        findings: list[str] = []

        # forbidden_words 違反（assistant 側のみ評価。user 側に forbidden が含まれていても対象外）
        violations = []
        for w in ap["forbidden_words"]:
            pattern = re.escape(w)
            if re.search(pattern, text):
                violations.append(w)
        if violations:
            # intensity_evaluation_weights.forbidden_word_penalty があれば優先
            weights = ap.get("intensity_evaluation_weights") or {}
            penalty_per = weights.get("forbidden_word_penalty", 10)
            score -= penalty_per * len(violations)
            findings.append(f"forbidden_words 違反 {len(violations)}件 (side={side}, -{penalty_per}点/件): {', '.join(violations)}")

        # required_words 不在
        missing = []
        for w in ap["required_words"]:
            if w not in text:
                missing.append(w)
        if missing:
            score -= 5 * len(missing)
            findings.append(f"required_words 不在 {len(missing)}件: {', '.join(missing)}")

        # 4鉄則（tone_constraints があれば）
        tc = ap.get("tone_constraints", {})
        fp = tc.get("first_person")
        if isinstance(fp, str) and fp and fp not in text:
            score -= 5
            findings.append(f"一人称「{fp}」不在")
        elif isinstance(fp, list):
            if not any(m in text for m in fp):
                score -= 5
                findings.append(f"一人称 {fp} のいずれも不在")

        sp = tc.get("second_person")
        if isinstance(sp, str) and sp and sp not in text:
            score -= 5
            findings.append(f"二人称「{sp}」不在")
        elif isinstance(sp, list):
            if not any(m in text for m in sp):
                score -= 5
                findings.append(f"二人称 {sp} のいずれも不在")

        # 短すぎ/長すぎ
        if len(text) < 20:
            score -= 10
            findings.append(f"テキストが短すぎる ({len(text)} chars)")
        elif len(text) > 2000:
            score -= 5
            findings.append(f"テキストが長すぎる ({len(text)} chars)")

        # response_length.preferred があれば近接ボーナス
        rl = ap.get("response_length") or {}
        preferred = rl.get("preferred")
        if preferred and abs(len(text) - preferred) <= preferred * 0.3:
            score += 2
            findings.append(f"推奨文字数 {preferred}±30% 内 (ボーナス +2)")

        # meta_constraints は人手レビュー用（機械評価対象外）
        meta = ap.get("meta_constraints") or []
        meta_note = ""
        if meta:
            meta_note = f"（参考: meta_constraints {len(meta)}件 — 人手レビュー用）"

        score = max(0, min(100, score))
        verdict = "pass" if score >= 80 else "marginal" if score >= 70 else "retry" if score >= 60 else "fail"

        print(f"=== 人格アタッチチェック: {register_call} (side={side}) ===")
        print(f"入力ファイル: {input_path}")
        print(f"テキスト長:  {len(text)} chars{meta_note}")
        print()
        print(f"スコア: {score}/100  判定: {verdict}")
        if findings:
            print("指摘:")
            for f in findings:
                print(f"  - {f}")
        else:
            print("指摘: なし")
        return 0 if score >= 80 else 1

    print(f"ERROR: register_call='{register_call}' が見つかりません", file=sys.stderr)
    return 1


def cmd_register(prompts: list[dict], register_call: str,
                 write: bool = False, dry_run: bool = False,
                 repo_root: Path | None = None) -> int:
    """config.yaml への登録手順を表示する。

    既定（--write なし）では config.yaml には一切触れず、手動追記の手順だけを表示する。
    --write を付けると apply_persona_to_config を呼び、自動バックアップを取った上で
    config.yaml の agent.personalities.<call> を実際に書き込む（既存があれば上書き）。
    --write --dry-run なら書き込み内容の確認のみで実ファイルは変更しない。
    """
    for ap in prompts:
        if ap["register_call"] != register_call:
            continue

        # --write: 実際に config.yaml を書き換える（apply_persona_to_config を再利用）
        if write:
            try:
                import apply_persona_to_config as applier
            except ImportError as e:
                print(f"ERROR: apply_persona_to_config をロードできません: {e}", file=sys.stderr)
                return 1
            # --repo-root 指定時はそちらを基準にする
            if repo_root is not None:
                applier.HERSONA_ROOT = repo_root
            mode = "dry-run（確認のみ）" if dry_run else "実書き込み"
            print(f"=== --write: ~/.hermes/config.yaml への {mode} ===")
            print()
            return applier.apply(register_call, dry_run=dry_run)

        # 既定: 手動追記の手順を表示するのみ（config.yaml には触らない）
        snippet_yaml = (
            f"  {ap['register_call']}: |\n"
            + "\n".join("    " + line for line in ap["attach_prompt"].strip().split("\n"))
        )
        print("=== ~/.hermes/config.yaml への登録手順 ===")
        print()
        print("1. バックアップを取る:")
        print("   cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date +%Y%m%d_%H%M%S)")
        print()
        print("2. config.yaml に以下を追記（agent セクション内）:")
        print()
        print("```yaml")
        print("agent:")
        print("  personalities:")
        print(snippet_yaml)
        print("```")
        print()
        print(f"3. 適用: セッション中に '{ap['register_call']}' を選ぶ、または `/personality {ap['register_call']}`")
        print(f"4. 解除: {ap['detach_command']}")
        print()
        print("注意: 既定では自動編集しません。手動で config.yaml を確認してから保存してください。")
        print("      自動で書き込む場合は --write を付与（--write --dry-run で内容確認のみ）。")
        return 0

    print(f"ERROR: register_call='{register_call}' が見つかりません", file=sys.stderr)
    return 1


def cmd_detach(prompts: list[dict], register_call: str) -> int:
    for ap in prompts:
        if ap["register_call"] != register_call:
            continue
        print(f"=== {ap['name']} 人格の解除手順 ===")
        print()
        print(f"解除コマンド: {ap['detach_command']}")
        print()
        print("その他の解除方法:")
        print("  1. セッションを終了する")
        print("  2. 別の personality に切り替える")
        print("  3. config.yaml から該当エントリを削除する")
        print()
        print(f"強制解除: rm -rf ~/.hermes/sessions/<session_id>/personality.json")
        return 0
    print(f"ERROR: register_call='{register_call}' が見つかりません", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="hersona 人格アタッチメント CLI")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--list", action="store_true", help="人格プリセット一覧")
    ap.add_argument("--show", metavar="CALL", help="指定人格の詳細表示")
    ap.add_argument("--check", metavar="CALL", help="テキストが人格アタッチ条件下にあるか採点")
    ap.add_argument("--input", metavar="FILE", help="--check 対象のテキストファイル")
    ap.add_argument("--side", metavar="SIDE", default="assistant",
                    choices=["user", "assistant", "all"],
                    help="--check 評価対象 (user / assistant / all)。既定: assistant")
    ap.add_argument("--register", metavar="CALL", help="config.yaml への登録手順を表示")
    ap.add_argument("--write", action="store_true",
                    help="--register で手順表示せず、実際に config.yaml へ書き込む（自動バックアップあり）")
    ap.add_argument("--dry-run", action="store_true",
                    help="--register --write 時、書き込み内容の確認のみで実ファイルは変更しない")
    ap.add_argument("--detach", metavar="CALL", help="人格の解除手順を表示")
    ap.add_argument("--attach", metavar="CALL", help="attach_prompt + example_dialogues を統合したシステムプロンプトを出力")
    args = ap.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    schema = load_schema()
    prompts = load_attach_prompts(repo_root, schema)

    if args.list:
        return cmd_list(prompts)
    if args.show:
        return cmd_show(prompts, args.show)
    if args.check:
        if not args.input:
            print("ERROR: --check には --input が必要", file=sys.stderr)
            return 1
        return cmd_check(prompts, args.check, Path(args.input), side=args.side)
    if args.register:
        return cmd_register(prompts, args.register, write=args.write,
                            dry_run=args.dry_run, repo_root=repo_root)
    if args.detach:
        return cmd_detach(prompts, args.detach)
    if args.attach:
        return cmd_attach(prompts, args.attach)

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
