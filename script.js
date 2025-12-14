// ============================
// Utility helpers
// ============================

// Build internal link (keeps user inside HornUpdates)
function buildArticleLink(sourceUrl) {
  return `reader.html?url=${encodeURIComponent(sourceUrl || "#")}`;
}
function parseTime(s) {
  const t = Date.parse(s || "");
  return Number.isFinite(t) ? t : 0;
}

function dedupeArticles(list) {
  const seen = new Set();
  const out = [];
  for (const a of list || []) {
    const key = (a.source_url || a.url || a.link || a.title || "").trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(a);
  }
  return out;
}

// Pick a featured story that rotates (doesn't repeat every load)
function pickFeatured(list) {
  const key = "hornupdates_last_featured_url";
  const last = localStorage.getItem(key);

  // Prefer something that isn't the same as last time
  let pick = list.find(a => (a.source_url || a.url) && (a.source_url || a.url) !== last);

  // Fallback to first item
  if (!pick) pick = list[0];

  if (pick) localStorage.setItem(key, pick.source_url || pick.url || "");
  return pick;
}

// Countries formatting
function formatCountries(countries) {
  if (!countries || (Array.isArray(countries) && countries.length === 0)) return "";
  return Array.isArray(countries) ? countries.join(" • ") : String(countries);
}

// Normalize backend article shape -> frontend expectations
function normalizeArticle(raw) {
  const countries =
    Array.isArray(raw.country_tags) && raw.country_tags.length
      ? raw.country_tags
      : (raw.countries || []);

  const topicTags = Array.isArray(raw.topic_tags) ? raw.topic_tags : [];
  const primaryTopic =
    topicTags[0] ||
    raw.topic ||
    raw.category ||
    "News";

  return {
    ...raw,
    countries,
    topic: primaryTopic,
    category: primaryTopic,
  };
}

// Format date as a nice short string (optional: you can tweak)
function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso; // fallback
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ============================
// Render functions
// ============================

// Render a standard story card (Latest section)
function renderStoryCard(article) {
  const countries = formatCountries(article.countries);
  const category = article.category || article.topic || "News";
  const published = formatDate(article.published_at || "");
  const sourceName = article.source_name || article.source || "";
  const title = article.title || "Untitled story";
  const summary = article.summary || article.excerpt || "";
  const href = buildArticleLink(article.source_url || article.link);

  return `
    <article class="story-card">
      <header class="story-header">
        <div class="story-tags">
          ${countries ? `<span class="story-countries">${countries}</span>` : ""}
          <span class="story-category">${category}</span>
        </div>
        <h3 class="story-title">
          <a class="card-link" href="${href}">
            ${title}
          </a>
        </h3>
      </header>
      ${summary ? `<p class="story-summary">${summary}</p>` : ""}
      <footer class="story-meta">
        ${sourceName ? `<span class="story-source">${sourceName}</span>` : ""}
        ${published ? `<span class="story-date">${published}</span>` : ""}
      </footer>
    </article>
  `;
}

// HERO MAIN STORY (big left side)
function renderHeroMain(article) {
  if (!article) return "";

  const countries = formatCountries(article.countries);
  const category = article.category || article.topic || "News";
  const published = formatDate(article.published_at || "");
  const title = article.title || "Untitled story";
  const summary = article.summary || "";
  const sourceName = article.source_name || article.source || "";
  const href = buildArticleLink(article.source_url || article.link);

  return `
    <article class="hero-main">
      <div class="hero-main-body">
        <div class="hero-main-tags">
          ${countries ? `<span class="hero-main-countries">${countries}</span>` : ""}
          <span class="hero-main-label">${category}</span>
        </div>
        <h2 class="hero-main-title">
          <a class="card-link" href="${href}">${title}</a>
        </h2>
        ${summary ? `<p class="hero-main-summary">${summary}</p>` : ""}
      </div>
      <footer class="hero-main-meta">
        ${sourceName ? `<span class="hero-main-source">${sourceName}</span>` : ""}
        ${published ? `<span class="hero-main-date">${published}</span>` : ""}
      </footer>
    </article>
  `;
}

// HERO SIDE STORIES (right column small cards)
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

// Breaking bar text (top strip)
function updateBreakingBar(article) {
  const bar = document.querySelector(".breaking-bar");
  if (!bar || !article) return;

  const countries = formatCountries(article.countries);
  const title = article.title || "";
  const href = buildArticleLink(article.source_url || article.link);

  const textEl = bar.querySelector(".breaking-text") || bar;
  textEl.innerHTML = `
    <span class="breaking-label">Breaking</span>
    ${countries ? `<span class="breaking-countries">${countries}</span>` : ""}
    <a class="breaking-link" href="${href}">${title}</a>
  `;
}

// ============================
// Filtering
// ============================

function filterArticles(allArticles, filterValue) {
  if (!filterValue || filterValue === "all") {
    return allArticles;
  }

  const fv = filterValue.toLowerCase();

  // Map simple buttons to backend-style topics
  const topicMap = {
    politics: "politics & governance",
    business: "business & economy",
    security: "security & conflict",
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

    // Match on topic/category
    if (cat.includes(mapped) || topic.includes(mapped) || joinedTags.includes(mapped)) {
      return true;
    }

    // Also allow filtering by country name
    const countries = Array.isArray(a.countries) ? a.countries : [];
    if (countries.some((c) => c.toLowerCase().includes(mapped))) {
      return true;
    }

    return false;
  });
}

function setupFilters(allArticles, renderLatestFn) {
  const buttons = Array.from(document.querySelectorAll(".filter-btn"));
  if (!buttons.length) return;

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const filterVal = btn.getAttribute("data-filter") || "all";

      // Toggle active state
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

document.addEventListener("DOMContentLoaded", () => {
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

  // Safety check
  if (!latestContainer && !heroMainSlot) {
    console.warn("HornUpdates: no target containers found in DOM.");
  }

  fetch("articles.json?v=" + Date.now())
    .then((res) => res.json())
    .then((data) => {
      const rawArticles = Array.isArray(data.articles) ? data.articles : data;
      let articles = rawArticles.map(normalizeArticle);

      // Sort newest -> oldest
      articles.sort((a, b) => {
        const da = new Date(a.published_at || 0).getTime();
        const db = new Date(b.published_at || 0).getTime();
        return db - da;
      });

      // HERO main + side
      const heroMainArticle = articles[0] || null;
      const heroSideArticles = articles.slice(1, 4); // up to 3 side stories

      if (heroMainSlot && heroMainArticle) {
        heroMainSlot.innerHTML = renderHeroMain(heroMainArticle);
      }

      if (heroSideSlot && heroSideArticles.length) {
        heroSideSlot.innerHTML = heroSideArticles.map(renderHeroSide).join("");
      }

      // Breaking bar (use heroMain or next best)
      updateBreakingBar(heroMainArticle || articles[0]);

      // Latest list renderer (used by filters too)
      function renderLatestList(list) {
        if (!latestContainer) return;
        latestContainer.innerHTML = list.map(renderStoryCard).join("");
      }

      // Initial latest list (skip hero articles)
      const latestArticles = articles.slice(1);
      renderLatestList(latestArticles);

      // Setup filters
      setupFilters(articles, renderLatestList);
    })
    .catch((err) => {
      console.error("HornUpdates: error loading articles.json", err);
    });
});
