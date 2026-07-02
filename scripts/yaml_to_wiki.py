#!/usr/bin/env python3
"""
yaml_to_wiki.py — hersona 属性 YAML を GitHub Wiki 用 Markdown 一覧に変換する。

各 YAML の display_name_ja / display_name_en / description_ja / description_en を
読み取り、以下の 6 ファイル (Home + 5 カテゴリ) を --output 配下に出力する。

  Home.md
  Personality.md
  Speech.md
  Archetype.md
  Hobby.md
  Visual.md

各行は GitHub の blob/main/ パスを直接指すので、wiki 閲覧者が YAML 本体に
ワンクリックで到達できる。Wiki は目次、attributes/ は本体という役割分担。

使用方法:
  python3 scripts/yaml_to_wiki.py [--attributes-dir DIR] [--output DIR] [--ref REF]

  --attributes-dir  既定: ./attributes
  --output          既定: ./wiki_build (hersona.wiki clone 先ではない、ローカルプレビュー用)
  --ref             既定: main (リンク先のブランチ/タグ/コミット SHA)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_OWNER = "shiro-0x"
REPO_NAME = "hersona"

# Wiki のページ名 → カテゴリディレクトリ名 (公式カテゴリと 1:1)
CATEGORIES = [
    ("personality", "Personality", "性格"),
    ("speech", "Speech", "口調"),
    ("archetype", "Archetype", "アーキタイプ"),
    ("hobby", "Hobby", "趣味・ライフスタイル"),
    ("visual", "Visual", "外見"),
]

# Wiki ページ名は GitHub 側でファイル名 .md とそのまま対応する。
# Wiki のタイトルは H1 で見せる。
WIKI_FILENAME = {
    "Home": "Home",
    "personality": "Personality",
    "speech": "Speech",
    "archetype": "Archetype",
    "hobby": "Hobby",
    "visual": "Visual",
}


def md_escape(text: str | None) -> str:
    """Markdown のテーブルセル用に | をエスケープし、改行をスペースへ。"""
    if text is None:
        return "—"
    s = str(text).replace("|", "\\|").replace("\n", " ").strip()
    return s if s else "—"


def yaml_link(attr_name: str, category: str, ref: str) -> str:
    """GitHub の attributes/<category>/<name>.yaml への直接リンクを生成。"""
    url = (
        f"https://github.com/{REPO_OWNER}/{REPO_NAME}/blob/{ref}"
        f"/attributes/{category}/{attr_name}.yaml"
    )
    return f"[`{attr_name}.yaml`]({url})"


def load_attributes(attributes_dir: Path) -> dict[str, list[tuple[str, dict]]]:
    """カテゴリ -> [(attr_name, yaml_dict), ...] を返す。"""
    out: dict[str, list[tuple[str, dict]]] = {}
    for cat_dir, _, _ in CATEGORIES:
        cat_path = attributes_dir / cat_dir
        if not cat_path.is_dir():
            out[cat_dir] = []
            continue
        items: list[tuple[str, dict]] = []
        for yaml_file in sorted(cat_path.glob("*.yaml")):
            try:
                with yaml_file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                print(f"[warn] {yaml_file}: YAML parse error: {e}", file=sys.stderr)
                continue
            items.append((yaml_file.stem, data))
        out[cat_dir] = items
    return out


def render_category_page(
    cat_dir: str,
    title_en: str,
    title_ja: str,
    items: list[tuple[str, dict]],
    ref: str,
) -> str:
    """1 カテゴリ分の Markdown ページを生成する。

    新 YAML 形式は display_name / description (英語のみ) のみ持っているため、
    「display_name | description | YAML リンク」の 3 列とする。
    """
    lines: list[str] = []
    lines.append(f"# {title_en} / {title_ja}")
    lines.append("")
    lines.append(
        f"All {len(items)} attributes. Click a YAML link to open the source file."
    )
    lines.append("")
    lines.append("| Display Name | Description | YAML |")
    lines.append("|---|---|---|")
    for attr_name, data in items:
        dn = data.get("display_name") or attr_name
        desc = data.get("description") or "—"
        link = yaml_link(attr_name, cat_dir, ref)
        lines.append(
            f"| {md_escape(dn)} | {md_escape(desc)} | {link} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_home_page(
    counts: dict[str, int], ref: str
) -> str:
    """Home.md (全体サマリ + カテゴリ説明 + 統計 + カテゴリページリンク) を生成する。"""
    lines: list[str] = []
    lines.append("# hersona Attribute Catalog")
    lines.append("")
    lines.append(
        "Catalog of hersona attributes — generic, work-agnostic building blocks "
        "for constructing characters. Each row links directly to the source YAML."
    )
    lines.append("")
    lines.append(f"- Repository: [{REPO_OWNER}/{REPO_NAME}](https://github.com/{REPO_OWNER}/{REPO_NAME})")
    lines.append(f"- Linked ref: `blob/{ref}/attributes/`")
    lines.append(f"- Total attributes: **{sum(counts.values())}**")
    lines.append("")
    lines.append("## Categories")
    lines.append("")
    lines.append("| Category | Count | Wiki page |")
    lines.append("|---|---:|---|")
    for cat_dir, title_en, title_ja in CATEGORIES:
        wiki_page = WIKI_FILENAME[cat_dir]
        lines.append(
            f"| {title_en} ({title_ja}) | {counts[cat_dir]} | "
            f"[{wiki_page}]({wiki_page}) |"
        )
    lines.append("")
    lines.append("## How to read")
    lines.append("")
    lines.append(
        "Each category page is a table of **Display Name | Description | YAML link**."
        " Click the YAML link to open `attributes/<category>/<name>.yaml` in the repository."
    )
    lines.append("")
    lines.append(
        "YAML files contain `core_traits`, `catchphrases`, `tone`, "
        "`compatible_archetypes`, `conflicts_with`, and more."
    )
    lines.append("")
    lines.append("## License")
    lines.append("")
    lines.append(
        "Public attributes: CC0. Source code: MIT. See the repository for details."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attributes-dir",
        default="attributes",
        help="attributes ディレクトリのルート (既定: ./attributes)",
    )
    parser.add_argument(
        "--output",
        default="wiki_build",
        help="出力先ディレクトリ (既定: ./wiki_build)",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="GitHub の blob リンクに使う ref (既定: main)",
    )
    args = parser.parse_args()

    attributes_dir = Path(args.attributes_dir).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not attributes_dir.is_dir():
        print(f"[error] attributes dir not found: {attributes_dir}", file=sys.stderr)
        return 1

    data = load_attributes(attributes_dir)
    counts = {cat: len(items) for cat, items in data.items()}

    # カテゴリ別ページ
    for cat_dir, title_en, title_ja in CATEGORIES:
        md = render_category_page(cat_dir, title_en, title_ja, data[cat_dir], args.ref)
        out_path = output_dir / f"{WIKI_FILENAME[cat_dir]}.md"
        out_path.write_text(md, encoding="utf-8")
        print(f"[ok] {out_path.relative_to(output_dir.parent)} ({counts[cat_dir]} rows)")

    # Home
    home_md = render_home_page(counts, args.ref)
    (output_dir / "Home.md").write_text(home_md, encoding="utf-8")
    print("[ok] Home.md")

    print(
        f"\nDone. {sum(counts.values())} attributes across "
        f"{sum(1 for c in counts.values() if c > 0)} categories → {output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
