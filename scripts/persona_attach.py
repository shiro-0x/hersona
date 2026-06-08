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


def cmd_check(prompts: list[dict], register_call: str, input_path: Path, side: str = "assistant",
              legacy_score: bool = False) -> int:
    """人格アタッチメント採点 (assistant 側デフォルト)。

    採点方式:
      - legacy_score=True: 旧「絶対減点式 (score = 100 - Σpenalty)」。後方互換用。
      - legacy_score=False (デフォルト): 新「重み付き合成 (score = Σweight[key] - penalties)」。
        forbidden 違反 1件で最大 60点 (40点満点分の全打ち消し + 20点持ち越しなし) に丸める。
    """
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

        # meta_constraints は人手レビュー用（機械評価対象外）
        meta = ap.get("meta_constraints") or []
        meta_note = ""
        if meta:
            meta_note = f"（参考: meta_constraints {len(meta)}件 — 人手レビュー用）"

        if legacy_score:
            return _legacy_score(ap, register_call, text, side, input_path, meta_note)
        return _weighted_score(ap, register_call, text, side, input_path, meta_note)

    print(f"ERROR: register_call='{register_call}' が見つかりません", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# 採点コア: 新方式（重み付き合成）と旧方式（絶対減点）
# ---------------------------------------------------------------------------

# デフォルト重み（重み付き合成用）— 仕様書 Part B
DEFAULT_WEIGHTS: dict[str, int] = {
    "forbidden": 40,
    "required": 20,
    "first_person": 10,
    "second_person": 10,
    "sentence_endings": 15,
    "free_description": 5,
}


def _resolve_weights(ap: dict) -> dict[str, int]:
    """yaml の intensity_evaluation_weights から重みを解決する。

    互換性:
      - 新フィールド: forbidden_weight / required_weight / tone_weight (dict)
        → 3 軸 (forbidden/required/tone) の満点配分。Wave1-T3 で導入 (commit 0d418a5)。
      - 旧フィールド: forbidden_word_penalty (絶対減点、_legacy_score で使用)
        → 新方式 (重み付き合成) では無視する。残しても安全 (新フィールドが優先)。
      - 何も無ければ DEFAULT_WEIGHTS (P0#9 仕様書推奨値)

    旧 yaml が vocab/tone/personality 比率しか持っていなかった場合 (Wave1-T3 移行前):
      → 新フィールドが未設定なので DEFAULT_WEIGHTS にフォールバック。
      → 旧 vocab/tone/personality キーは新方式では意味を持たないため無視。
    """
    weights = dict(DEFAULT_WEIGHTS)
    iew = ap.get("intensity_evaluation_weights") or {}
    if not isinstance(iew, dict):
        return weights
    # 新方式: forbidden_weight / required_weight / tone_weight
    if "forbidden_weight" in iew:
        try:
            weights["forbidden"] = int(iew["forbidden_weight"])
        except (TypeError, ValueError):
            pass
    if "required_weight" in iew:
        try:
            weights["required"] = int(iew["required_weight"])
        except (TypeError, ValueError):
            pass
    if isinstance(iew.get("tone_weight"), dict):
        tw = iew["tone_weight"]
        for k in ("first_person", "second_person", "sentence_endings", "free_description"):
            if k in tw:
                try:
                    weights[k] = int(tw[k])
                except (TypeError, ValueError):
                    pass
    return weights


def _legacy_score(ap: dict, register_call: str, text: str, side: str,
                  input_path: Path, meta_note: str) -> int:
    """旧: score = 100 - Σpenalty の絶対減点式 (後方互換)"""
    score = 100
    findings: list[str] = []

    violations: list[str] = []
    for w in ap.get("forbidden_words", []):
        pattern = re.escape(w)
        if re.search(pattern, text):
            violations.append(w)
    if violations:
        weights = ap.get("intensity_evaluation_weights") or {}
        penalty_per = weights.get("forbidden_word_penalty", 10)
        score -= penalty_per * len(violations)
        findings.append(f"forbidden_words 違反 {len(violations)}件 (side={side}, -{penalty_per}点/件): {', '.join(violations)}")

    missing: list[str] = []
    for w in ap.get("required_words", []):
        if w not in text:
            missing.append(w)
    if missing:
        score -= 5 * len(missing)
        findings.append(f"required_words 不在 {len(missing)}件: {', '.join(missing)}")

    tc = ap.get("tone_constraints", {}) or {}
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

    if len(text) < 20:
        score -= 10
        findings.append(f"テキストが短すぎる ({len(text)} chars)")
    elif len(text) > 2000:
        score -= 5
        findings.append(f"テキストが長すぎる ({len(text)} chars)")

    rl = ap.get("response_length") or {}
    preferred = rl.get("preferred")
    if preferred and abs(len(text) - preferred) <= preferred * 0.3:
        score += 2
        findings.append(f"推奨文字数 {preferred}±30% 内 (ボーナス +2)")

    score = max(0, min(100, score))
    verdict = "pass" if score >= 80 else "marginal" if score >= 70 else "retry" if score >= 60 else "fail"
    return _print_result(register_call, side, input_path, text, score, verdict, findings, meta_note, mode="legacy")


def _weighted_score(ap: dict, register_call: str, text: str, side: str,
                    input_path: Path, meta_note: str) -> int:
    """新: score = Σweight[key] - penalties の重み付き合成

    仕様:
      - forbidden 違反 1件で 60点上限 (40点満点消失 + α)
      - 5軸の加重加算で 0-100 点に分布
      - 95+ & forbidden 0件 は人手レビュー推奨の警告
    """
    weights = _resolve_weights(ap)
    score = 0
    findings: list[str] = []

    # 1) forbidden
    fwords = ap.get("forbidden_words", []) or []
    violations = [w for w in fwords if w and w in text]
    if violations:
        # 1件目で weights["forbidden"] を全失、2件目以降 10点ずつ追加減点（最大 40点）
        score += 0  # 加算しない（最大消失）
        extra = min(40, (len(violations) - 1) * 10)
        score -= extra
        findings.append(f"forbidden_words 違反 {len(violations)}件: {', '.join(violations)} (重み{weights['forbidden']}全失 + 追加 -{extra})")
    else:
        score += weights["forbidden"]

    # 2) required
    rwords = ap.get("required_words", []) or []
    missing = [w for w in rwords if w and w not in text]
    if not missing:
        score += weights["required"]
    else:
        score += max(0, weights["required"] - len(missing) * 5)
        findings.append(f"required_words 不在 {len(missing)}件: {', '.join(missing)} (-{len(missing) * 5})")

    # 3) first_person
    tc = ap.get("tone_constraints", {}) or {}
    fp = tc.get("first_person")
    fp_hit = False
    if isinstance(fp, str) and fp:
        fp_hit = fp in text
    elif isinstance(fp, list) and fp:
        fp_hit = any(m in text for m in fp)
    if fp_hit:
        score += weights["first_person"]
    elif fp:
        findings.append(f"first_person ({fp}) 出現なし")

    # 4) second_person
    sp = tc.get("second_person")
    sp_hit = False
    if isinstance(sp, str) and sp:
        sp_hit = sp in text
    elif isinstance(sp, list) and sp:
        sp_hit = any(m in text for m in sp)
    if sp_hit:
        score += weights["second_person"]
    elif sp:
        findings.append(f"second_person ({sp}) 出現なし")

    # 5) sentence_endings (regex マッチ)
    # 仕様 (Wave1-T3 レビュー指摘 2 で確定):
    #   - yaml 側は語尾を「～の」「～のね」のように波ダッシュ (U+301C) をプレースホルダとして付けて書いてよい
    #     (Linter/視認性のため。実際のセリフに波ダッシュが入ることは稀)。
    #   - 照合前に lstrip("～") で先頭の波ダッシュを全剥がし → rstrip("。") で末尾句点を全剥がし、
    #     実 LLM 出力 (例: 「・・・ごめんなさい。今は、言葉が出ないの」) と比較する。
    #   - 入力に波ダッシュが混入した場合 (例: 「～ごめんなさい」) でも、yaml 側の語尾にも先頭に
    #     波ダッシュがあれば「～ごめんなさいの」のような一致も許容される (lstrip 後でも yaml 側の
    #     プレースホルダ由来のトークンが残るため)。実 LLM 出力では波ダッシュ混入は事実上無いため
    #     安全側に倒す。lstrip の挙動は「先頭の連続する波ダッシュを全剥がし」なので、yaml 側が
    #     プレースホルダ 1 個なら 1 個剥がれる、2 個なら 2 個剥がれる (実例: 全 3 キャラ yaml は
    #     プレースホルダ 1 個)。
    #   - フォールバック (re.error) は旧い「in 演算子」単純一致。escape 失敗時の安全網。
    endings = tc.get("sentence_endings", []) or []
    if endings:
        try:
            pattern = re.compile("|".join(re.escape(e.lstrip("～").rstrip("。")) for e in endings))
            if pattern.search(text):
                score += weights["sentence_endings"]
            else:
                findings.append(f"sentence_endings ({endings[:3]}...) 出現なし")
        except re.error:
            # フォールバック: 旧い単純 in
            hit = any(e.lstrip("～").rstrip("。") in text for e in endings)
            if hit:
                score += weights["sentence_endings"]
            else:
                findings.append(f"sentence_endings ({endings[:3]}...) 出現なし")
    else:
        # sentence_endings 未定義なら満点（重みだけ加算）
        score += weights["sentence_endings"]

    # 6) free_description (response_length への近接)
    rlen = ap.get("response_length") or {}
    preferred = rlen.get("preferred")
    text_len = len(text)
    if preferred and abs(text_len - preferred) / preferred <= 0.3:
        score += weights["free_description"]
    elif text_len < 20:
        score -= 10
        findings.append(f"短すぎ ({text_len} < 20)")
    elif text_len > 2000:
        score -= 5
        findings.append(f"長すぎ ({text_len} > 2000)")

    # 7) 「です・ます」多用ペナルティ（キャラが forbid しない場合の安全側）
    desu_masu = len(re.findall(r"(です|ます)[。ね]", text))
    if desu_masu >= 3:
        score -= 5
        findings.append(f"「です・ます」多用 {desu_masu}件")

    # 8) 偽陽性警告: 95+ & forbidden 0件は人手レビュー推奨
    if score >= 95 and not violations:
        findings.append("警告: スコア 95+ & forbidden 0件: 偽陽性を疑って人手レビュー推奨")

    score = max(0, min(100, score))
    verdict = "pass" if score >= 80 else "marginal" if score >= 70 else "retry" if score >= 60 else "fail"
    return _print_result(register_call, side, input_path, text, score, verdict, findings, meta_note, mode="weighted")


def _print_result(register_call: str, side: str, input_path: Path, text: str,
                  score: int, verdict: str, findings: list[str], meta_note: str,
                  mode: str) -> int:
    """採点結果の標準出力 (新・旧両方式で共通)"""
    print(f"=== 人格アタッチチェック: {register_call} (side={side}, mode={mode}) ===")
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
    ap.add_argument("--legacy-score", action="store_true",
                    help="--check で旧『絶対減点式 score=100-Σpenalty』を使う（後方互換・デフォルトは新『重み付き合成』）")
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
        return cmd_check(prompts, args.check, Path(args.input), side=args.side, legacy_score=args.legacy_score)
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
