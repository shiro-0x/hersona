#!/usr/bin/env python3
"""hersona 人格アタッチメント CLI

YAML/MD から persona_attach_prompt フィールドを抽出し、表示・チェック・登録手順案内を行う。

使用方法:
    python scripts/persona_attach.py --list
    python scripts/persona_attach.py --show melina
    python scripts/persona_attach.py --check melina --input sample.txt
    python scripts/persona_attach.py --register melina
    python scripts/persona_attach.py --detach melina
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


def cmd_check(prompts: list[dict], register_call: str, input_path: Path) -> int:
    for ap in prompts:
        if ap["register_call"] != register_call:
            continue
        text = input_path.read_text(encoding="utf-8")
        score = 100
        findings: list[str] = []

        # forbidden_words 違反
        violations = []
        for w in ap["forbidden_words"]:
            # 単語境界で判定（部分一致を避ける）
            pattern = re.escape(w)
            if re.search(pattern, text):
                violations.append(w)
        if violations:
            score -= 10 * len(violations)
            findings.append(f"forbidden_words 違反 {len(violations)}件: {', '.join(violations)}")

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
        if tc.get("first_person") and tc["first_person"] not in text:
            score -= 5
            findings.append(f"一人称「{tc['first_person']}」不在")
        if tc.get("second_person") and tc["second_person"] not in text:
            score -= 5
            findings.append(f"二人称「{tc['second_person']}」不在")

        # 短すぎ/長すぎ
        if len(text) < 20:
            score -= 10
            findings.append(f"テキストが短すぎる ({len(text)} chars)")
        elif len(text) > 2000:
            score -= 5
            findings.append(f"テキストが長すぎる ({len(text)} chars)")

        score = max(0, min(100, score))
        verdict = "pass" if score >= 80 else "marginal" if score >= 70 else "retry" if score >= 60 else "fail"

        print(f"=== 人格アタッチチェック: {register_call} ===")
        print(f"入力ファイル: {input_path}")
        print(f"テキスト長:  {len(text)} chars")
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


def cmd_register(prompts: list[dict], register_call: str) -> int:
    """config.yaml への登録手順を表示（自動編集はしない）"""
    for ap in prompts:
        if ap["register_call"] != register_call:
            continue
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
        print("注意: 自動編集はしません。必ず手動で config.yaml を確認してから保存してください。")
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
    ap.add_argument("--register", metavar="CALL", help="config.yaml への登録手順を表示")
    ap.add_argument("--detach", metavar="CALL", help="人格の解除手順を表示")
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
        return cmd_check(prompts, args.check, Path(args.input))
    if args.register:
        return cmd_register(prompts, args.register)
    if args.detach:
        return cmd_detach(prompts, args.detach)

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
