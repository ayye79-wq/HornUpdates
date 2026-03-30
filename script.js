// ============================
// Utility helpers
// ============================

function buildArticleLink(sourceUrl) {
  return `reader.html?url=${encodeURIComponent(sourceUrl || "#")}`;
}

function formatCountries(countries) {
  if (!countries || (Array.isArray(countries) && countries.length === 0)) return "";
  return Array.isArray(countries) ? countries.join(" • ") : String(countries);
}

function normalizeArticle(raw) {
  const countries =
    Array.isArray(raw.country_tags) && raw.country_tags.length
      ? raw.country_tags
      : (raw.countries || []);

  const topicTags = Array.isArray(raw.topic_tags) ? raw.topic_tags : [];
  const primaryTopic = topicTags[0] || raw.topic || raw.category || "News";

  return { ...raw, countries, topic: primaryTopic, category: primaryTopic };
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

// ============================
// Context / Background matching
// ============================

let _contextTemplates = null;

async function loadContextTemplates() {
  if (_contextTemplates) return _contextTemplates;
  try {
    const res = await fetch("why_matters_templates.json");
    _contextTemplates = await res.json();
  } catch (e) {
    _contextTemplates = { groups: [], default: null };
  }
  return _contextTemplates;
}

function getContextForArticle(article, templates) {
  if (!templates || !templates.groups) return null;

  const text = [
    article.title || "",
    article.summary || "",
    ...(article.topic_tags || []),
    ...(article.country_tags || []),
  ].join(" ").toLowerCase();

  // Sort groups by priority descending
  const sorted = [...templates.groups].sort((a, b) => (b.priority || 0) - (a.priority || 0));

  for (const group of sorted) {
    const { match, templates: tmplList } = group;
    if (!match || !tmplList || !tmplList.length) continue;

    const keywordsMatch = (match.any_keyword || []).some(kw => text.includes(kw.toLowerCase()));
    const catMatch = (match.any_category || []).some(cat =>
      text.includes(cat.toLowerCase())
    );

    if (keywordsMatch || catMatch) {
      // Pick template deterministically by title hash
      const idx = Math.abs(simpleHash(article.title || "")) % tmplList.length;
      return tmplList[idx].text;
    }
  }

  return (templates.default && templates.default.text) || null;
}

function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0;
  }
  return hash;
}

// ============================
// Language label
// ============================

function langLabel(article) {
  const lang = article.language || "en";
  if (lang === "ar") {
    return `<span class="lang-pill lang-ar" title="Arabic">AR</span>`;
  }
  return "";
}

// ============================
// Render functions
// ============================

function renderContextBlock(contextText) {
  if (!contextText) return "";
  return `
    <details class="context-box">
      <summary class="context-toggle">
        <span class="context-icon">&#9432;</span> Background &amp; Context
      </summary>
      <p class="context-text">${contextText}</p>
    </details>
  `;
}

function renderStoryCard(article, contextText) {
  const countries = formatCountries(article.countries);
  const category = article.category || article.topic || "News";
  const published = formatDate(article.published_at || "");
  const sourceName = article.source_name || article.source || "";
  const title = article.title || "Untitled story";
  const summary = article.summary || article.excerpt || "";
  const href = buildArticleLink(article.source_url || article.link);
  const lang = langLabel(article);

  return `
    <article class="story-card">
      <header class="story-header">
        <div class="story-tags">
          ${countries ? `<span class="story-countries">${countries}</span>` : ""}
          <span class="story-category">${category}</span>
          ${lang}
        </div>
        <h3 class="story-title">
          <a class="card-link" href="${href}">${title}</a>
        </h3>
      </header>
      ${summary ? `<p class="story-summary">${summary}</p>` : ""}
      ${renderContextBlock(contextText)}
      <footer class="story-meta">
        ${sourceName ? `<span class="story-source">${sourceName}</span>` : ""}
        ${published ? `<span class="story-date">${published}</span>` : ""}
      </footer>
    </article>
  `;
}

function renderHeroMain(article, contextText) {
  if (!article) return "";

  const countries = formatCountries(article.countries);
  const category = article.category || article.topic || "News";
  const published = formatDate(article.published_at || "");
  const title = article.title || "Untitled story";
  const summary = article.summary || "";
  const sourceName = article.source_name || article.source || "";
  const href = buildArticleLink(article.source_url || article.link);
  const lang = langLabel(article);

  return `
    <article class="hero-main">
      <div class="hero-main-body">
        <div class="hero-main-tags">
          ${countries ? `<span class="hero-main-countries">${countries}</span>` : ""}
          <span class="hero-main-label">${category}</span>
          ${lang}
        </div>
        <h2 class="hero-main-title">
          <a class="card-link" href="${href}">${title}</a>
        </h2>
        ${summary ? `<p class="hero-main-summary">${summary}</p>` : ""}
        ${renderContextBlock(contextText)}
      </div>
      <footer class="hero-main-meta">
        ${sourceName ? `<span class="hero-main-source">${sourceName}</span>` : ""}
        ${published ? `<span class="hero-main-date">${published}</span>` : ""}
      </footer>
    </article>
  `;
}

function renderHeroSide(article) {
  if (!article) return "";
  const countries = formatCountries(article.countries);
  const category = article.category || article.topic || "News";
  const published = formatDate(article.published_at || "");
  const title = article.title || "Untitled story";
  const sourceName = article.source_name || article.source || "";
  const href = buildArticleLink(article.source_url || article.link);

  return `
    <article class="hero-side-card">
      <div class="hero-side-body">
        <div class="hero-side-tags">
          ${countries ? `<span class="hero-side-countries">${countries}</span>` : ""}
          <span class="hero-side-category">${category}</span>
        </div>
        <h3 class="hero-side-title">
          <a class="card-link" href="${href}">${title}</a>
        </h3>
      </div>
      <footer class="hero-side-meta">
        ${sourceName ? `<span class="hero-side-source">${sourceName}</span>` : ""}
        ${published ? `<span class="hero-side-date">${published}</span>` : ""}
      </footer>
    </article>
  `;
}

function updateBreakingBar(article) {
  const bar = document.querySelector(".breaking-bar");
  if (!bar || !article) return;

  const countries = formatCountries(article.countries);
  const title = article.title || "";
  const href = buildArticleLink(article.source_url || article.link);

  const textEl = bar.querySelector(".breaking-text") || bar;
  textEl.innerHTML = `
    <span class="breaking-label">Latest Signal</span>
    ${countries ? `<span class="breaking-countries">${countries}</span>` : ""}
    <a class="breaking-link" href="${href}">${title}</a>
  `;
}

// ============================
// Filtering
// ============================

function filterArticles(allArticles, filterValue) {
  if (!filterValue || filterValue === "all") return allArticles;

  const fv = filterValue.toLowerCase();

  const topicMap = {
    politics: "politics & governance",
    business: "business & economy",
    security: "security & conflict",
    humanitarian: "humanitarian",
    diplomacy: "diplomacy",
    climate: "climate & environment",
    health: "health",
    culture: "culture",
    diaspora: "diaspora",
  };

  const mapped = topicMap[fv] || fv;

  return allArticles.filter((a) => {
    const cat = (a.category || "").toLowerCase();
    const topic = (a.topic || "").toLowerCase();
    const joinedTags = Array.isArray(a.topic_tags)
      ? a.topic_tags.join(" ").toLowerCase()
      : "";

    if (cat.includes(mapped) || topic.includes(mapped) || joinedTags.includes(mapped)) return true;

    const countries = Array.isArray(a.countries) ? a.countries : [];
    if (countries.some((c) => c.toLowerCase().includes(mapped))) return true;

    return false;
  });
}

function setupFilters(allArticles, renderLatestFn) {
  const buttons = Array.from(document.querySelectorAll(".filter-btn, .filter-pill"));
  if (!buttons.length) return;

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const filterVal = btn.getAttribute("data-filter") || "all";
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const filtered = filterArticles(allArticles, filterVal.toLowerCase());
      renderLatestFn(filtered);
    });
  });
}

// ============================
// Main load + render pipeline
// ============================

document.addEventListener("DOMContentLoaded", async () => {
  const heroMainSlot =
    document.querySelector('[data-slot="hero-main"]') ||
    document.querySelector(".hero-main-slot") ||
    document.querySelector("#hero-main");

  const heroSideSlot =
    document.querySelector('[data-slot="hero-side"]') ||
    document.querySelector(".hero-side-slot") ||
    document.querySelector("#hero-side");

  const latestContainer =
    document.querySelector("#latest-list") ||
    document.querySelector(".latest-stories");

  if (!latestContainer && !heroMainSlot) {
    console.warn("HornUpdates: no target containers found in DOM.");
  }

  // Load both data sources in parallel
  const [data, templates] = await Promise.all([
    fetch("articles.json?v=" + Date.now()).then(r => r.json()).catch(() => ({ articles: [] })),
    loadContextTemplates(),
  ]);

  const rawArticles = Array.isArray(data.articles) ? data.articles : data;
  let articles = rawArticles.map(normalizeArticle);

  articles.sort((a, b) => {
    const da = new Date(a.published_at || 0).getTime();
    const db = new Date(b.published_at || 0).getTime();
    return db - da;
  });

  const heroMainArticle = articles[0] || null;
  const heroSideArticles = articles.slice(1, 4);

  if (heroMainSlot && heroMainArticle) {
    const ctx = getContextForArticle(heroMainArticle, templates);
    heroMainSlot.innerHTML = renderHeroMain(heroMainArticle, ctx);
  }

  if (heroSideSlot && heroSideArticles.length) {
    heroSideSlot.innerHTML = heroSideArticles.map(renderHeroSide).join("");
  }

  updateBreakingBar(heroMainArticle || articles[0]);

  function renderLatestList(list) {
    if (!latestContainer) return;
    latestContainer.innerHTML = list.map(a => {
      const ctx = getContextForArticle(a, templates);
      return renderStoryCard(a, ctx);
    }).join("");
  }

  const latestArticles = articles.slice(1);
  renderLatestList(latestArticles);

  setupFilters(articles, renderLatestList);
});
