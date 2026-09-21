import fs from 'node:fs/promises';

const required = name => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
};

const escapeHtml = value => String(value ?? '')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const inbox = JSON.parse(await fs.readFile(new URL('../data/ai-inbox.json', import.meta.url), 'utf8'));
const candidates = (inbox.candidates || [])
  .filter(item => item.status === 'candidate' && item.url && item.title)
  .slice(0, 8);

if (!candidates.length) {
  console.log('No AI-news candidates are available for approval.');
  process.exit(0);
}

const recipient = required('APPROVAL_EMAIL_TO');
const sender = process.env.APPROVAL_EMAIL_FROM?.trim() || 'HornUpdates Approvals <approvals@hornupdates.com>';
const pullRequestUrl = required('APPROVAL_PR_URL');

const rows = candidates.map((item, index) => `
  <tr>
    <td style="padding:16px 0;border-bottom:1px solid #dbe4ee">
      <div style="font:700 12px Arial,sans-serif;color:#087ea4;text-transform:uppercase;letter-spacing:.08em">${escapeHtml(item.source || 'Source')} · Candidate ${index + 1}</div>
      <div style="margin:6px 0 8px;font:700 18px/1.35 Arial,sans-serif;color:#0b1727">${escapeHtml(item.title)}</div>
      <a href="${escapeHtml(item.url)}" style="font:600 14px Arial,sans-serif;color:#087ea4">Open original source →</a>
    </td>
  </tr>`).join('');

const html = `<!doctype html>
<html><body style="margin:0;background:#eef3f7;padding:24px">
  <div style="max-width:680px;margin:auto;background:#fff;border-radius:14px;overflow:hidden;border:1px solid #dbe4ee">
    <div style="background:#07111f;padding:28px 32px;color:#fff">
      <div style="font:700 22px Arial,sans-serif">HornUpdates AI</div>
      <div style="margin-top:6px;font:14px Arial,sans-serif;color:#a9bfd4">Editorial approval request</div>
    </div>
    <div style="padding:28px 32px">
      <h1 style="margin:0 0 10px;font:700 26px Arial,sans-serif;color:#0b1727">New stories need your review</h1>
      <p style="margin:0 0 18px;font:16px/1.55 Arial,sans-serif;color:#415267">The automated collector found ${candidates.length} candidate stories. Check the original sources, then approve the candidate-inbox pull request or close it if the selection should be rejected.</p>
      <table role="presentation" style="width:100%;border-collapse:collapse">${rows}</table>
      <div style="margin-top:26px">
        <a href="${escapeHtml(pullRequestUrl)}" style="display:inline-block;background:#087ea4;color:#fff;text-decoration:none;border-radius:8px;padding:13px 18px;font:700 15px Arial,sans-serif">Review approval request</a>
      </div>
      <p style="margin:20px 0 0;font:13px/1.5 Arial,sans-serif;color:#637487">Approving this request stores the reviewed candidate inbox. It does not silently publish an article. Public stories still require promotion into the verified HornUpdates feed.</p>
    </div>
  </div>
</body></html>`;

if (process.env.APPROVAL_EMAIL_DRY_RUN === '1') {
  console.log(`Approval email preview is valid for ${recipient} with ${candidates.length} candidates.`);
  process.exit(0);
}

const apiKey = required('RESEND_API_KEY');

const response = await fetch('https://api.resend.com/emails', {
  method: 'POST',
  headers: {
    authorization: `Bearer ${apiKey}`,
    'content-type': 'application/json'
  },
  body: JSON.stringify({
    from: sender,
    to: [recipient],
    subject: `HornUpdates: ${candidates.length} AI stories need approval`,
    html
  })
});

const payload = await response.json().catch(() => ({}));
if (!response.ok) throw new Error(`Resend rejected the approval email (${response.status}): ${JSON.stringify(payload)}`);
console.log(`Approval email sent to ${recipient}; Resend id ${payload.id || 'unknown'}.`);
