async function loadArticles() {
  const featuredEl = document.getElementById("featured-story");
  const listEl = document.getElementById("stories-list");

  try {
    const res = await fetch("articles.json");
    if (!res.ok) throw new Error("Could not load articles.json");

    const articles = await res.json();

    if (!articles || articles.length === 0) {
      featuredEl.innerHTML = "<p>No stories available.</p>";
      return;
    }

    // --- Featured story = first item ---
    const featured = articles[0];
    featuredEl.innerHTML = renderStoryCard(featured, true);

    // --- Latest stories = the rest ---
    listEl.innerHTML = "";
    articles.slice(1).forEach(article => {
      const wrapper = document.createElement("article");
      wrapper.className = "story-card";
      wrapper.dataset.topic = article.topic || "all";
      wrapper.innerHTML = renderStoryCard(article, false);
      listEl.appendChild(wrapper);
    });

    // Wire up filters AFTER rendering
    setupFilters();

  } catch (err) {
    console.error(err);
    featuredEl.innerHTML = "<p>Failed to load stories.</p>";
  }
}

// Render HTML for a story
function renderStoryCard(article, isFeatured) {
  const countries = Array.isArray(article.countries)
    ? article.countries.join(" • ")
    : (article.countries || "");

  const category = article.category || "";
  const topic = article.topic || "";
  const published = article.published_at || "";
  const summary = article.summary || "";
  const sourceUrl = article.source_url || "#";

  return `
    <div class="card-category">
      ${countries}${countries && category ? " • " : ""}${category}
    </div>
    <h3 class="card-title">${article.title}</h3>
    <div class="card-meta">
      ${topic ? `${topic} · ` : ""}${published}
    </div>
    <p class="card-text">${summary}</p>
    <a class="card-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">
      Read on News →
    </a>
  `;
}

// Set up filter buttons
function setupFilters() {
  const buttons = document.querySelectorAll(".filter-btn");
  const stories = document.querySelectorAll("#stories-list .story-card");

  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      const filter = btn.dataset.filter; // "all", "Politics", "Business", etc.

      // Toggle button active state
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      // Filter stories
      stories.forEach(card => {
        const topic = (card.dataset.topic || "").toLowerCase();
        if (filter === "all" || topic === filter.toLowerCase()) {
          card.style.display = "";
        } else {
          card.style.display = "none";
        }
      });
    });
  });
}

// Run on load
loadArticles();
