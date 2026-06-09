/* ===== hersona demo — client logic =====
 * data.json / showcase.json を読み、属性カタログ・before/after デモ・
 * ブレンド注入プロンプト生成・診断を描画する。
 * render_blend / recommend のロジックは hersona (Python) に忠実に移植している。
 */
"use strict";

const CAT_ORDER = ["personality", "speech", "archetype", "hobby"];
const CAT_LABEL = {
  personality: { ja: "性格", en: "Personality" },
  speech: { ja: "口調", en: "Speech" },
  archetype: { ja: "アーキタイプ", en: "Archetype" },
  hobby: { ja: "趣味", en: "Hobby" },
};
const WEIGHTS = ["mild", "moderate", "strong"];

const state = {
  lang: "both",
  data: null,
  showcase: null,
  byName: new Map(),
  galleryFilter: "all",
  blendFilter: "all",
  demo: { name: "tsundere", weight: "moderate" },
  blend: { names: [], weight: "moderate" },
  quiz: { answers: {}, index: 0 },
};

/* ---------- boot ---------- */
async function boot() {
  const [data, showcase] = await Promise.all([
    fetch("data.json").then((r) => r.json()),
    fetch("showcase.json").then((r) => r.json()),
  ]);
  state.data = data;
  state.showcase = showcase;
  data.attributes.forEach((a) => state.byName.set(a.attribute_name, a));

  setLang(localStorage.getItem("hersona-lang") || "both");
  initLangToggle();
  renderDemo();
  renderGallery();
  renderBlend();
  renderQuiz();
  initModal();
  document.getElementById("attr-count").textContent = data.attributes.length;
}

/* ---------- language ---------- */
function setLang(lang) {
  state.lang = lang;
  document.body.dataset.lang = lang;
  localStorage.setItem("hersona-lang", lang);
  document.querySelectorAll(".lang-toggle button").forEach((b) =>
    b.classList.toggle("active", b.dataset.lang === lang)
  );
  // data-ja/data-en chrome
  document.querySelectorAll("[data-ja]").forEach((el) => {
    if (lang === "en" && el.dataset.en) el.textContent = el.dataset.en;
    else if (lang === "ja" && el.dataset.ja) el.textContent = el.dataset.ja;
    else if (lang === "both" && el.dataset.ja && el.dataset.en)
      el.textContent = el.dataset.en === el.dataset.ja ? el.dataset.ja : `${el.dataset.ja} / ${el.dataset.en}`;
  });
}
function initLangToggle() {
  document.querySelectorAll(".lang-toggle button").forEach((b) =>
    b.addEventListener("click", () => {
      setLang(b.dataset.lang);
      // re-render dynamic content that bakes language in
      renderDemo();
      renderGallery();
      renderBlend();
      renderQuiz();
    })
  );
}
// pick localized string honoring lang mode (both => ja main + en sub handled by caller)
function L(ja, en) {
  if (state.lang === "en") return en || ja;
  return ja;
}

/* ---------- DEMO (before/after) ---------- */
function renderDemo() {
  const pickers = document.getElementById("demo-pickers");
  pickers.innerHTML = "";
  state.showcase.items.forEach((it) => {
    const a = state.byName.get(it.attribute_name);
    const btn = document.createElement("button");
    btn.className = "demo-pick" + (it.attribute_name === state.demo.name ? " active" : "");
    btn.innerHTML = `${a.display_name_ja}<small>${a.display_name_en}</small>`;
    btn.addEventListener("click", () => {
      state.demo.name = it.attribute_name;
      renderDemo();
    });
    pickers.appendChild(btn);
  });

  const item = state.showcase.items.find((i) => i.attribute_name === state.demo.name);
  const a = state.byName.get(state.demo.name);
  const w = state.demo.weight;

  document.getElementById("demo-prompt").innerHTML = bilingual(item.prompt.ja, item.prompt.en);
  document.getElementById("demo-before").innerHTML = bilingual(item.before.ja, item.before.en);
  const after = item.after[w];
  document.getElementById("demo-after").innerHTML = bilingual(after.ja, after.en);
  const lbl = document.getElementById("demo-after-label");
  lbl.innerHTML =
    L(`属性適用：${a.display_name_ja}`, `Applied: ${a.display_name_en}`) +
    ` <code style="font-family:'JetBrains Mono';color:var(--accent-3)">(${w})</code>`;

  // weight segment
  document.querySelectorAll("#demo-weight button").forEach((b) => {
    b.classList.toggle("active", b.dataset.w === w);
    b.onclick = () => {
      state.demo.weight = b.dataset.w;
      renderDemo();
    };
  });
}
// render ja (+ en subline when in both mode)
function bilingual(ja, en) {
  if (state.lang === "en") return escapeHtml(en || ja);
  if (state.lang === "ja") return escapeHtml(ja);
  return `${escapeHtml(ja)}<span class="en-sub">${escapeHtml(en || "")}</span>`;
}

/* ---------- GALLERY ---------- */
function renderGallery() {
  const filters = document.getElementById("filters");
  filters.innerHTML = "";
  makeChip(filters, "all", L("すべて", "All"), state.galleryFilter, (v) => {
    state.galleryFilter = v;
    renderGallery();
  });
  CAT_ORDER.forEach((c) => {
    const n = state.data.attributes.filter((a) => a.attribute_category === c).length;
    makeChip(filters, c, `${CAT_LABEL[c][state.lang === "en" ? "en" : "ja"]} (${n})`, state.galleryFilter, (v) => {
      state.galleryFilter = v;
      renderGallery();
    });
  });

  const grid = document.getElementById("gallery-grid");
  grid.innerHTML = "";
  state.data.attributes
    .filter((a) => state.galleryFilter === "all" || a.attribute_category === state.galleryFilter)
    .forEach((a) => grid.appendChild(card(a)));
}
function makeChip(parent, value, label, current, onClick) {
  const c = document.createElement("button");
  c.className = "chip" + (value === current ? " active" : "");
  c.textContent = label;
  c.addEventListener("click", () => onClick(value));
  parent.appendChild(c);
}
function card(a) {
  const el = document.createElement("div");
  el.className = "card";
  el.style.setProperty("--c", `var(--cat-${a.attribute_category})`);
  const desc = state.lang === "en" ? a.description_en : a.description_ja;
  el.innerHTML = `
    <div class="w-badge">${a.weight_dimension}</div>
    <div class="card-cat">${CAT_LABEL[a.attribute_category][state.lang === "en" ? "en" : "ja"]}</div>
    <div class="card-name">${a.display_name_ja} <span class="en">${a.display_name_en}</span></div>
    <p class="card-desc">${escapeHtml(desc)}</p>
    <div class="card-tags">${(a.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>`;
  el.addEventListener("click", () => openModal(a));
  return el;
}

/* ---------- BLEND ---------- */
function renderBlend() {
  // filters
  const bf = document.getElementById("blend-filters");
  bf.innerHTML = "";
  makeChip(bf, "all", L("すべて", "All"), state.blendFilter, (v) => {
    state.blendFilter = v;
    renderBlend();
  });
  CAT_ORDER.forEach((c) =>
    makeChip(bf, c, CAT_LABEL[c][state.lang === "en" ? "en" : "ja"], state.blendFilter, (v) => {
      state.blendFilter = v;
      renderBlend();
    })
  );

  // options
  const opts = document.getElementById("blend-options");
  opts.innerHTML = "";
  state.data.attributes
    .filter((a) => state.blendFilter === "all" || a.attribute_category === state.blendFilter)
    .forEach((a) => {
      const on = state.blend.names.includes(a.attribute_name);
      const o = document.createElement("button");
      o.className = "opt" + (on ? " on" : "");
      o.innerHTML = `<span>${a.display_name_ja}</span><small>${a.attribute_category} · ${a.display_name_en}</small>`;
      o.addEventListener("click", () => toggleBlend(a.attribute_name));
      opts.appendChild(o);
    });

  // chosen pills
  const chosen = document.getElementById("blend-chosen");
  chosen.innerHTML = "";
  if (state.blend.names.length === 0) {
    chosen.innerHTML = `<span class="blend-empty">${L("属性を選んでください", "Pick attributes to combine")}</span>`;
  } else {
    state.blend.names.forEach((n) => {
      const a = state.byName.get(n);
      const p = document.createElement("span");
      p.className = "chosen-pill";
      p.innerHTML = `${a.display_name_ja} <button aria-label="remove">×</button>`;
      p.querySelector("button").addEventListener("click", () => toggleBlend(n));
      chosen.appendChild(p);
    });
  }

  // weight
  document.querySelectorAll("#blend-weight button").forEach((b) => {
    b.classList.toggle("active", b.dataset.w === state.blend.weight);
    b.onclick = () => {
      state.blend.weight = b.dataset.w;
      renderBlend();
    };
  });

  renderBlendPrompt();
}
function toggleBlend(name) {
  const i = state.blend.names.indexOf(name);
  if (i >= 0) state.blend.names.splice(i, 1);
  else state.blend.names.push(name);
  renderBlend();
}
function renderBlendPrompt() {
  const conflictBox = document.getElementById("blend-conflict");
  const box = document.getElementById("blend-prompt");
  if (state.blend.names.length === 0) {
    conflictBox.innerHTML = "";
    box.textContent = L(
      "← 左から属性を選ぶと、ここに system prompt 注入ブロックが生成されます。",
      "← Select attributes on the left to generate a system-prompt injection block here."
    );
    return;
  }
  const attrs = state.blend.names.map((n) => state.byName.get(n));
  const conflicts = checkBlend(state.blend.names);
  conflictBox.innerHTML = conflicts.length
    ? `<div class="conflict-warn">⚠ ${L("conflict 検出", "Conflict detected")}: ${conflicts
        .map(([a, b]) => `${a} ⇔ ${b}`)
        .join(" / ")}</div>`
    : "";
  box.textContent = renderPrompt(attrs, conflicts, state.blend.weight);
}

document.getElementById("blend-clear").addEventListener("click", () => {
  state.blend.names = [];
  renderBlend();
});
document.getElementById("blend-copy").addEventListener("click", () => {
  const txt = document.getElementById("blend-prompt").textContent;
  if (!state.blend.names.length) return;
  navigator.clipboard.writeText(txt).then(() => toast(L("コピーしました", "Copied!")));
});

/* ===== render_blend port (hersona/core/attach.py) ===== */
function conflictsBetween(aName, bName) {
  const a = state.byName.get(aName);
  const b = state.byName.get(bName);
  const aw = a.conflicts_with || [];
  const bw = b.conflicts_with || [];
  return aw.includes(bName) || bw.includes(aName);
}
function checkBlend(names) {
  const out = [];
  for (let i = 0; i < names.length; i++)
    for (let j = i + 1; j < names.length; j++)
      if (conflictsBetween(names[i], names[j])) out.push([names[i], names[j]]);
  return out;
}
function catchphraseSubset(list, level) {
  const ratio = state.data.catchphrase_ratio[level] ?? 0;
  if (!list || !list.length || ratio <= 0) return [];
  if (ratio >= 1) return list.slice();
  const k = Math.max(1, Math.round(list.length * ratio));
  return list.slice(0, k);
}
function mergeList(attrs, key) {
  const seen = new Set();
  const out = [];
  attrs.forEach((a) => (a[key] || []).forEach((it) => {
    if (!seen.has(it)) { seen.add(it); out.push(it); }
  }));
  return out;
}
function firstStr(attrs, key) {
  for (const a of attrs) if (typeof a[key] === "string" && a[key]) return a[key];
  return "";
}
function renderPrompt(attrs, conflicts, level) {
  const lines = ["# hersona 属性ブレンド"];
  const display = attrs.map((a) => `${a.attribute_category}/${a.attribute_name}`).join(" + ");
  lines.push(`以下の属性を統合した人格として応答する: ${display}`, "");
  lines.push(`## 強度: ${level}`, state.data.weight_guidance[level]);

  if (conflicts.length) {
    lines.push("", "⚠ conflict 検出 (不誠実さ過剰の可能性):");
    conflicts.forEach(([a, b]) => lines.push(`  - ${a} ⇔ ${b}`));
  }

  const coreTraits = mergeList(attrs, "core_traits");
  const catchphrases = catchphraseSubset(mergeList(attrs, "catchphrases"), level);
  const sentenceEndings = mergeList(attrs, "sentence_endings");
  const secondPerson = firstStr(attrs, "second_person");
  const tones = attrs.filter((a) => a.tone).map((a) => a.tone);

  if (coreTraits.length) { lines.push("", "## core_traits"); coreTraits.forEach((t) => lines.push(`- ${t}`)); }
  if (secondPerson) lines.push("", `## 二人称: ${secondPerson}`);
  if (sentenceEndings.length) lines.push("", "## 語尾: " + sentenceEndings.join(" / "));
  if (catchphrases.length) { lines.push("", "## catchphrases"); catchphrases.forEach((c) => lines.push(`- ${c}`)); }
  if (tones.length) { lines.push("", "## tone"); tones.forEach((t) => lines.push(`- ${t}`)); }

  return lines.join("\n");
}

/* ---------- QUIZ (recommend port) ---------- */
function renderQuiz() {
  const body = document.getElementById("quiz-body");
  const result = document.getElementById("quiz-result");
  const quiz = state.data.quiz;

  if (state.quiz.index >= quiz.length) {
    body.hidden = true;
    result.hidden = false;
    renderQuizResult();
    return;
  }
  body.hidden = false;
  result.hidden = true;

  const q = quiz[state.quiz.index];
  const pct = Math.round((state.quiz.index / quiz.length) * 100);
  body.innerHTML = `
    <div class="quiz-progress">Q${state.quiz.index + 1} / ${quiz.length}</div>
    <div class="quiz-bar"><i style="width:${pct}%"></i></div>
    <h3 class="quiz-q">${escapeHtml(q.prompt)}</h3>
    <div class="quiz-opts"></div>`;
  const opts = body.querySelector(".quiz-opts");
  q.options.forEach((o, idx) => {
    const b = document.createElement("button");
    b.className = "quiz-opt";
    b.textContent = o.label;
    b.addEventListener("click", () => {
      state.quiz.answers[q.id] = idx;
      state.quiz.index++;
      renderQuiz();
    });
    opts.appendChild(b);
  });
}
// score_answers + recommend (conflict-aware), faithful to recommend.py
function scoreAnswers() {
  const scores = {};
  const quiz = state.data.quiz;
  Object.entries(state.quiz.answers).forEach(([qid, oi]) => {
    const q = quiz.find((x) => x.id === qid);
    if (!q) return;
    Object.entries(q.options[oi].weights).forEach(([attr, w]) => {
      scores[attr] = (scores[attr] || 0) + w;
    });
  });
  return scores;
}
function recommend() {
  const scores = scoreAnswers();
  // top per category (personality/speech/archetype only — matches python)
  const byCat = {};
  Object.entries(scores).forEach(([name, score]) => {
    const a = state.byName.get(name);
    if (score <= 0 || !a) return;
    (byCat[a.attribute_category] = byCat[a.attribute_category] || []).push([name, score]);
  });
  const candidates = [];
  ["personality", "speech", "archetype"].forEach((c) => {
    const ranked = (byCat[c] || []).sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]));
    if (ranked.length) candidates.push(ranked[0]);
  });
  candidates.sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]));
  const blend = [];
  const dropped = [];
  candidates.forEach(([name]) => {
    const conf = blend.filter((b) => conflictsBetween(name, b));
    if (conf.length) dropped.push([name, conf.join(", ")]);
    else blend.push(name);
  });
  return { blend, scores, dropped };
}
function suggestWeight(score) {
  if (score <= 0) return "none";
  if (score < 1.5) return "mild";
  if (score < 3.0) return "moderate";
  return "strong";
}
function renderQuizResult() {
  const { blend, scores, dropped } = recommend();
  const result = document.getElementById("quiz-result");
  const pills = blend
    .map((n) => {
      const a = state.byName.get(n);
      const w = suggestWeight(scores[n] || 0);
      return `<div class="result-pill"><b>${a.display_name_ja}</b><small>${a.attribute_category} · ${w} · score ${(
        scores[n] || 0
      ).toFixed(1)}</small></div>`;
    })
    .join("");
  const droppedHtml = dropped.length
    ? `<p class="result-dropped">⚠ ${dropped
        .map(([n, why]) => `${n} (${L("除外", "dropped")}: ${why})`)
        .join(" / ")}</p>`
    : "";
  result.innerHTML = `
    <h3>${L("あなた好みのブレンド", "Your recommended blend")}</h3>
    <p style="color:var(--ink-dim);margin:0">${L(
      "相性チェック済み。そのままブレンド生成に送れます。",
      "Conflict-checked. Send it straight to the blend generator."
    )}</p>
    <div class="result-blend">${pills || `<span class="blend-empty">${L("回答から推薦が作れませんでした", "No recommendation from these answers")}</span>`}</div>
    ${droppedHtml}
    <div class="quiz-actions">
      <button class="btn btn-primary" id="quiz-apply">${L("このブレンドを生成 →", "Generate this blend →")}</button>
      <button class="btn btn-ghost" id="quiz-retry">${L("もう一度", "Retry")}</button>
    </div>`;
  document.getElementById("quiz-retry").addEventListener("click", () => {
    state.quiz = { answers: {}, index: 0 };
    renderQuiz();
  });
  document.getElementById("quiz-apply").addEventListener("click", () => {
    state.blend.names = blend.slice();
    if (blend.length) state.blend.weight = suggestWeight(Math.max(...blend.map((n) => scores[n] || 0)));
    renderBlend();
    document.getElementById("blend").scrollIntoView({ behavior: "smooth" });
  });
}

/* ---------- MODAL ---------- */
function initModal() {
  const modal = document.getElementById("modal");
  modal.querySelectorAll("[data-close]").forEach((el) =>
    el.addEventListener("click", () => (modal.hidden = true))
  );
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") modal.hidden = true;
  });
}
function openModal(a) {
  const body = document.getElementById("modal-body");
  const block = (title, items) =>
    items && items.length
      ? `<div class="m-block"><h4>${title}</h4><div class="m-list">${items
          .map((i) => `<span>${escapeHtml(i)}</span>`)
          .join("")}</div></div>`
      : "";
  body.innerHTML = `
    <div class="m-cat" style="--c:var(--cat-${a.attribute_category})">${a.attribute_category}</div>
    <h3 class="m-name">${a.display_name_ja} <span class="en">${a.display_name_en}</span></h3>
    <p class="m-desc">${escapeHtml(a.description_ja)}<span class="en">${escapeHtml(a.description_en)}</span></p>
    <div class="m-meta">
      <span>${L("強度次元", "Weight")}: <code>${a.weight_dimension}</code></span>
      ${a.typical_value_range ? `<span>${L("典型値", "Range")}: <code>${a.typical_value_range}</code></span>` : ""}
    </div>
    ${block("core_traits", a.core_traits)}
    ${a.tone ? `<div class="m-block"><h4>tone</h4><p style="margin:0;color:var(--ink-dim)">${escapeHtml(a.tone)}</p></div>` : ""}
    ${block("catchphrases", a.catchphrases)}
    ${block(L("併用しやすい", "compatible"), a.compatible_archetypes)}
    ${block(L("conflict (排他)", "conflicts_with"), a.conflicts_with)}
    ${block("tags", a.tags)}
    <button class="btn btn-primary m-add" id="m-add">${
      state.blend.names.includes(a.attribute_name)
        ? L("ブレンドから外す", "Remove from blend")
        : L("ブレンドに追加 →", "Add to blend →")
    }</button>`;
  document.getElementById("m-add").addEventListener("click", () => {
    toggleBlend(a.attribute_name);
    document.getElementById("modal").hidden = true;
    document.getElementById("blend").scrollIntoView({ behavior: "smooth" });
  });
  document.getElementById("modal").hidden = false;
}

/* ---------- utils ---------- */
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
let toastTimer;
function toast(msg) {
  let t = document.querySelector(".toast");
  if (!t) {
    t = document.createElement("div");
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 1600);
}

boot();
