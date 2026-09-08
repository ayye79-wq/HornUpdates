(function () {
  function updateConsent(value) {
    var granted = value === 'accepted';
    localStorage.setItem('hu_cookie_consent', value);
    if (window.gtag) {
      window.gtag('consent', 'update', {
        ad_storage: granted ? 'granted' : 'denied',
        analytics_storage: granted ? 'granted' : 'denied',
        ad_user_data: granted ? 'granted' : 'denied',
        ad_personalization: granted ? 'granted' : 'denied'
      });
    }
  }

  if (localStorage.getItem('hu_cookie_consent')) return;
  var b = document.createElement('div');
  b.id = 'hu-cookie-banner';
  b.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:#111827;color:#e5e7eb;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;z-index:9999;border-top:2px solid rgba(245,158,11,.4);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:.88rem;line-height:1.5;';
  b.setAttribute('role', 'dialog');
  b.setAttribute('aria-label', 'Cookie choices');
  b.innerHTML = '<p style="margin:0;flex:1;min-width:220px;">Choose whether Horn Updates may use optional analytics and advertising cookies. Essential site functions do not require them. See our <a href="/privacy.html" style="color:#60a5fa;text-decoration:underline;">Privacy Policy</a>.</p>'
    + '<div style="display:flex;gap:8px;flex-shrink:0;">'
    + '<button id="hu-cookie-reject" style="background:rgba(255,255,255,.1);color:#fff;border:1px solid #6b7280;border-radius:8px;padding:8px 14px;font-weight:700;font-size:.85rem;cursor:pointer;white-space:nowrap;">Reject optional</button>'
    + '<button id="hu-cookie-accept" style="background:#f59e0b;color:#111827;border:none;border-radius:8px;padding:8px 18px;font-weight:700;font-size:.85rem;cursor:pointer;white-space:nowrap;">Accept optional</button>'
    + '</div>';
  document.body.appendChild(b);
  document.getElementById('hu-cookie-accept').addEventListener('click', function () {
    updateConsent('accepted');
    b.style.display = 'none';
  });
  document.getElementById('hu-cookie-reject').addEventListener('click', function () {
    updateConsent('rejected');
    b.style.display = 'none';
  });
})();
