(async function () {
  const root = document.querySelector('[data-ai-news]');
  if (!root) return;

  const escapeHtml = (value = '') => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
  const categoryClass = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

  try {
    const response = await fetch('/data/ai-news.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const stories = Array.isArray(data.stories) ? data.stories.filter(s => s.status === 'verified') : [];

    root.innerHTML = stories.slice(0, 6).map((story, index) => `
      <article class="${index === 0 ? 'ai-lead-card' : 'ai-card'}">
        <span class="tag ${categoryClass(story.category)}">${escapeHtml(story.category)}</span>
        <h3><a href="${escapeHtml(story.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(story.title)}</a></h3>
        <p>${escapeHtml(story.summary)}</p>
        <div class="why-matters"><strong>Why it matters:</strong> ${escapeHtml(story.why_it_matters)}</div>
        <div class="story-meta">${escapeHtml(story.source)} · ${escapeHtml(story.published)}</div>
      </article>`).join('');

    const updated = document.querySelector('[data-ai-updated]');
    if (updated && data.updated_at) {
      const d = new Date(data.updated_at);
      updated.textContent = `Verified feed · Updated ${d.toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'})}`;
    }
  } catch (error) {
    console.error('Horn Updates AI feed failed:', error);
    root.innerHTML = '<p class="feed-error">The live AI feed is temporarily unavailable. Please check back shortly.</p>';
  }
})();
