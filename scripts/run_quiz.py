#!/usr/bin/env python3
"""hersona 診断クイズ 非対話ヘルパー (TTY-less / batch / CI 用).

LLM 主軸の hersona-recommend-quiz スキル (SKILL.md) と対になる Python ヘルパー。
9 問全ての回答を引数または stdin から受け取り、`hersona recommend --answers ... --explain --json`
を subprocess で実行して、JSON を Markdown 整形して stdout に出力する。

Usage:
    # 1) 引数モード (事前回答あり)
    python3 scripts/run_quiz.py --answers "distance=1,emotion=2,speech=3,role=0,hobby=4,appearance=2,lifestyle=1,interaction=3,cultural=4"

    # 2) stdin モード (qid=index を 1 行ずつ、空行で finish)
    printf "distance=1\\nemotion=2\\n...\\ncultural=4\\n\\n" | python3 scripts/run_quiz.py

    # 3) --apply 付き (注入ブロックも表示)
    python3 scripts/run_quiz.py --answers "..." --apply

    # 4) --json 付き (raw JSON)
    python3 scripts/run_quiz.py --answers "..." --json

Pitfalls 対応 (hersona-recommend-quiz SKILL.md 参照):
- Q1: YAML は実行時に動的読み込み (選択肢ハードコード禁止)
- Q2: ユーザー入力は 1 始まり、内部は 0 始まり
- Q3: 9 個揃うまで CLI を叩かない
- Q4: blend 空のフォールバック
- Q5: summary=null のフォールバック
- Q6: alternatives は {dropped, alternative, score} のオブジェクト形式
- Q7: cwd = hersona プロジェクトルート
- Q8: hersona コマンドを使う (python -m hersona は不可)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# scripts/run_quiz.py の 2 つ上の階層が hersona プロジェクトルート
#   scripts/run_quiz.py
#   ../                      = <project_root>
PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUIZ_YAML = PROJECT_ROOT / "hersona" / "data" / "quiz" / "recommend_quiz.yaml"


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def load_quiz_ids() -> list[str]:
    """recommend_quiz.yaml から 9 問の ID リストを取得 (出現順維持)."""
    if not QUIZ_YAML.exists():
        sys.stderr.write(f"ERROR: クイズ YAML が見つかりません: {QUIZ_YAML}\n")
        sys.exit(2)
    with QUIZ_YAML.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    questions = data.get("questions") or []
    return [q["id"] for q in questions if "id" in q]


# ---------------------------------------------------------------------------
# Answer parsing
# ---------------------------------------------------------------------------


def parse_answer_string(s: str) -> dict[str, int]:
    """`distance=1,emotion=2` 形式の文字列を {qid: index} (0 始まり) に変換.

    Raises:
        ValueError: フォーマット不正または未知の qid.
    """
    out: dict[str, int] = {}
    valid_ids = set(load_quiz_ids())
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"フォーマット不正: '{chunk}' (期待: qid=index)")
        qid, idx_raw = chunk.split("=", 1)
        qid = qid.strip()
        idx_raw = idx_raw.strip()
        if qid not in valid_ids:
            raise ValueError(f"未知の qid: '{qid}' (有効: {sorted(valid_ids)})")
        try:
            idx = int(idx_raw)
        except ValueError as e:
            raise ValueError(f"index が整数でない: '{idx_raw}' (qid={qid})") from e
        if idx < 0:
            raise ValueError(f"index が負数: {idx} (qid={qid})")
        out[qid] = idx  # 0 始まりで保持 (CLI にも 0 始まりで渡す)
    return out


def read_stdin_answers() -> dict[str, int]:
    """stdin から `qid=index` を 1 行ずつ読み、空行で finish する.

    Raises:
        ValueError: フォーマット不正.
    """
    answers: dict[str, int] = {}
    sys.stderr.write("(qid=index を 1 行ずつ入力。空行で finish)\n")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            break
        # 1 行に複数カンマ区切りも許容
        try:
            parsed = parse_answer_string(line)
        except ValueError as e:
            sys.stderr.write(f"ERROR: {e}\n")
            sys.exit(2)
        answers.update(parsed)
    return answers


# ---------------------------------------------------------------------------
# hersona CLI invocation
# ---------------------------------------------------------------------------


def run_hersona_recommend(answers: dict[str, int], *, apply: bool) -> dict[str, Any]:
    """`hersona recommend` を subprocess で実行し JSON を dict で返す."""
    answers_str = ",".join(f"{qid}={idx}" for qid, idx in answers.items())
    cmd = ["hersona", "recommend", "--answers", answers_str, "--explain", "--json"]
    if apply:
        cmd.append("--apply")
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        sys.stderr.write(
            "ERROR: `hersona` コマンドが見つかりません。`uv pip install -e .` を実行してください。\n"
        )
        sys.exit(3)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"ERROR: hersona CLI 失敗 (exit {e.returncode}):\n{e.stderr}\n")
        sys.exit(4)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"ERROR: hersona CLI 出力が JSON として解釈できません: {e}\n")
        sys.stderr.write(f"stdout: {proc.stdout[:500]}\n")
        sys.exit(5)


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(result: dict[str, Any], apply: bool, apply_block: str = "") -> str:
    """JSON 結果を Telegram 安全な Markdown (ラベル+値 箇条書き) に整形."""
    lines: list[str] = []

    blend = result.get("blend") or []
    scores = result.get("scores") or {}
    rationale = result.get("rationale") or {}
    alternatives = result.get("alternatives") or []
    weight = result.get("weight_suggestion") or "?"
    summary = result.get("summary")

    # --- ヘッダ
    lines.append("## 推薦結果")
    lines.append("")

    # --- blend 空フォールバック (Pitfall Q4)
    if not blend:
        lines.append("**採用された属性 blend**: （なし）")
        lines.append("")
        lines.append("マッチする属性が見つかりませんでした。回答を変えて再挑戦してください。")
        return "\n".join(lines) + "\n"

    # --- 採用 blend
    lines.append("**採用された属性 blend**:")
    for name in blend:
        score = scores.get(name, 0.0)
        lines.append(f"- {name}（スコア {score:.2f}）")
    lines.append("")

    # --- rationale
    lines.append("**各属性の根拠（rationale）**:")
    for name in blend:
        reasons = rationale.get(name) or []
        if reasons:
            lines.append(f"- {name} を選んだ理由:")
            for r in reasons:
                lines.append(f"  - {r}")
        else:
            lines.append(f"- {name} を選んだ理由: （データなし）")
    lines.append("")

    # --- alternatives
    if alternatives:
        lines.append("**落選した属性の代替案（alternatives）**:")
        for alt in alternatives:
            if not isinstance(alt, dict):
                # 念のためタプル形式もケア
                try:
                    dropped, alternative, score = alt  # type: ignore[misc]
                    lines.append(f"- {dropped} の代わりに → {alternative}（スコア {score:.2f}）")
                except Exception:
                    lines.append(f"- {alt}")
                continue
            dropped = alt.get("dropped", "?")
            alternative = alt.get("alternative", "?")
            score = alt.get("score", 0.0)
            lines.append(f"- {dropped} の代わりに → {alternative}（スコア {score:.2f}）")
        lines.append("")

    # --- summary (Pitfall Q5)
    lines.append("**1 行サマリ**:")
    if summary:
        lines.append(f"> {summary}")
    else:
        lines.append("> （サマリ生成に失敗）")
    lines.append("")

    # --- weight_suggestion
    lines.append(f"**推奨強度**: {weight}")
    lines.append("")

    # --- --apply 時の注入ブロック
    if apply and apply_block:
        lines.append("---")
        lines.append("")
        lines.append("**注入ブロック（システムプロンプトにそのまま貼れます）**:")
        lines.append("")
        lines.append("```")
        lines.append(apply_block.rstrip())
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="hersona 診断クイズ 非対話ヘルパー (TTY-less / batch / CI 用)"
    )
    parser.add_argument(
        "--answers",
        type=str,
        default="",
        help="回答を `distance=1,emotion=2,...` 形式で指定 (0 始まり)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="注入ブロックも表示 (hersona recommend --apply 相当)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="raw JSON を stdout に出す (整形なし)",
    )
    args = parser.parse_args(argv)

    # --- 回答収集
    if args.answers:
        try:
            answers = parse_answer_string(args.answers)
        except ValueError as e:
            sys.stderr.write(f"ERROR: {e}\n")
            return 2
    elif not sys.stdin.isatty():
        # stdin モード (TTY が無いとき自動分岐)
        answers = read_stdin_answers()
    else:
        sys.stderr.write("ERROR: --answers または stdin 経由で回答を渡してください。\n")
        parser.print_help(sys.stderr)
        return 2

    # --- 9 問チェック
    expected = load_quiz_ids()
    missing = [qid for qid in expected if qid not in answers]
    if missing:
        sys.stderr.write(f"ERROR: 回答が未入力の qid: {missing}\n")
        return 2

    # --- CLI 実行
    result = run_hersona_recommend(answers, apply=args.apply)

    # --- 出力
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # --apply 時の注入ブロック抽出 (hersona CLI の stdout には JSON と注入ブロックが
    # 混ざって出力されるケースに備え、JSON 部分は parse で取り除いた上で別途得る)
    apply_block = ""
    if args.apply:
        # --json を消して --apply のみで再実行し、注入ブロックだけを取得
        answers_str = ",".join(f"{qid}={idx}" for qid, idx in answers.items())
        try:
            proc = subprocess.run(
                ["hersona", "recommend", "--answers", answers_str, "--apply"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            apply_block = proc.stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            apply_block = ""

    print(render_markdown(result, apply=args.apply, apply_block=apply_block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
