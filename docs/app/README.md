# hersona demo site

English: [`README.en.md`](./README.en.md)

`hersona` の価値（エージェントに規格化された性格を一行で着せる）を体感するための
**静的デモサイト**。GitHub Pages で配信できる（バックエンド不要）。

## 構成

| ファイル | 役割 |
|---|---|
| `index.html` | ページ本体（日英併記。ヘッダーの `日本語 / EN / 併記` で切替） |
| `style.css` | スタイル |
| `app.js` | 属性カタログ・before/after デモ・ブレンド注入プロンプト生成・診断のロジック |
| `data.json` | **自動生成**。`attributes/**/*.yaml` + 診断クイズ (BASE=ja と英語ペルソナ用 `quiz_en` の両方) + 強度ガイダンスを書き出したもの |
| `showcase.json` | before/after 体験デモ用の事前収録応答（手書き・日英・強度3段階） |

`app.js` の `renderPrompt` / `recommend` は `hersona/core/attach.py` ・
`hersona/core/recommend.py` のロジックを忠実に移植している（出力一致を確認済み）。

## セクション

1. **体験デモ** — 同じ問いに、属性適用前/後でどう変わるかを並べて表示。強度スライダーあり。
2. **属性カタログ** — 345 属性をカテゴリで絞り込み、カードをクリックで詳細（core_traits / catchphrases / tone / 相性）。
3. **ブレンド & 注入プロンプト生成** — 複数属性を選んで合成。conflict を自動警告し、system prompt 注入ブロックをコピー可能。
4. **診断** — 9 問に答えると相性チェック済みのブレンドを推薦し、そのまま生成へ送るか、注入ブロックを直接コピーできる。表示言語 en では英語 speech 属性へ導線する別クイズ (`quiz_en`) を使う。

## データの再生成

`attributes/` を編集したら、`data.json` を再生成してコミットする:

```bash
python scripts/build_site.py          # docs/app/data.json を再生成
python scripts/build_site.py --check  # CI 用: 最新かどうか検証
```

> `build_site.py` は PyYAML のみ必要（`jsonschema` 不要）。

## ローカル確認

```bash
cd docs/app && python3 -m http.server 8000
# → http://localhost:8000
```

## デプロイ

GitHub Pages は `/docs` フォルダを配信する（ランディングは `docs/index.html`、
デモアプリは本ディレクトリ `docs/app/`）。リポジトリの
**Settings → Pages → Build and deployment → Source** を **Deploy from a branch**、
ブランチ `main` / フォルダ `/docs` に設定すること。
