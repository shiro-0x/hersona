"""W2: recommend_quiz.yaml から英語ペルソナ用 recommend_quiz.en.yaml を導出する。

ベースクイズ (ja ペルソナ構成) に以下の変換を適用して書き出す:
1. ja speech 属性への weight を全設問から除去 (en ペルソナに ja 話法を混ぜない)
2. `speech` 設問の選択肢を英語 speech 5 種 (formal/casual/blunt/southern_us/british) に差替
3. 除去で空になる選択肢に en speech の weight を補填
   - interaction「Old-fashioned and formal」 → formal_en
   - cultural「Rooted in Kyoto culture」 → 英国伝統の選択肢に差替 (british_en)

ベースクイズを変更した場合は本スクリプトを再実行して en 版を再導出すること。
質問 ID は ベースと同一 (`--answers` のキー互換)。
"""
from __future__ import annotations

import glob
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
BASE = REPO / "hersona" / "data" / "quiz" / "recommend_quiz.yaml"
OUT = REPO / "hersona" / "data" / "quiz" / "recommend_quiz.en.yaml"

HEADER = """\
# hersona 診断クイズ — 英語ペルソナ版 (W2: ロケール別クイズ)
#
# scripts/_oneoff/gen_quiz_en.py が recommend_quiz.yaml から導出した生成物。
# 直接編集せず、ベースクイズを更新して再生成すること。
#
# ベースとの差分:
# - ja speech 属性への weight を除去 (英語ペルソナに日本語話法を混ぜない)
# - `speech` 設問は英語 speech 5 種 (formal/casual/blunt/southern_us/british _en)
# - interaction「Old-fashioned and formal」→ formal_en、cultural は英国伝統に差替
# - 質問 ID はベースと同一 (`--answers` キー互換)。表示言語 en のとき
#   recommend.quiz_for_lang() が本ファイルをロードする。
"""

# 差し替える speech 設問の選択肢 (英語 speech 5 種)
EN_SPEECH_OPTIONS = [
    {
        "label": "Polished and courteous",
        "i18n": {"ja": {"label": "上品で丁重な英語"}},
        "weights": {"formal_en": "STRONG"},
    },
    {
        "label": "Relaxed and friendly",
        "i18n": {"ja": {"label": "くだけて親しみやすい英語"}},
        "weights": {"casual_en": "STRONG"},
    },
    {
        "label": "Terse and direct",
        "i18n": {"ja": {"label": "端的でストレートな英語"}},
        "weights": {"blunt_en": "STRONG"},
    },
    {
        "label": "A warm Southern drawl",
        "i18n": {"ja": {"label": "温かい米南部訛り"}},
        "weights": {"southern_us_en": "STRONG"},
    },
    {
        "label": "Dry British wit",
        "i18n": {"ja": {"label": "辛口で英国風"}},
        "weights": {"british_en": "STRONG"},
    },
]

# 英国文化の選択肢 (cultural「Rooted in Kyoto culture」の差し替え)
BRITISH_CULTURAL_OPTION = {
    "label": "Rooted in British tradition",
    "i18n": {"ja": {"label": "英国の伝統が根付く"}},
    "weights": {"british_en": "STRONG", "mentor": "WEAK"},
}


def _speech_langs() -> dict[str, str]:
    """speech 属性名 → content_lang のマップ。"""
    langs: dict[str, str] = {}
    for f in glob.glob(str(REPO / "attributes" / "speech" / "*.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        langs[d["attribute_name"]] = d.get("content_lang") or "ja"
    return langs


def main() -> int:
    speech_langs = _speech_langs()
    data = yaml.safe_load(open(BASE, encoding="utf-8"))

    data["description"] = (
        "9-question quiz for English personas (routes to content_lang=en speech); "
        "derived from recommend_quiz.yaml by gen_quiz_en.py"
    )

    for q in data["questions"]:
        if q["id"] == "speech":
            q["options"] = [dict(o) for o in EN_SPEECH_OPTIONS]
            continue
        for opt in q["options"]:
            if q["id"] == "cultural" and opt["label"] == "Rooted in Kyoto culture":
                opt.clear()
                opt.update(BRITISH_CULTURAL_OPTION)
                continue
            weights = opt.get("weights", {})
            kept = {
                a: w
                for a, w in weights.items()
                if speech_langs.get(a, "en") == "en" or a not in speech_langs
            }
            if q["id"] == "interaction" and opt["label"] == "Old-fashioned and formal":
                kept["formal_en"] = "STRONG"
            if not kept:
                raise SystemExit(f"empty option after strip: {q['id']} / {opt['label']}")
            opt["weights"] = kept

    body = yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000
    )
    OUT.write_text(HEADER + "\n" + body, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
