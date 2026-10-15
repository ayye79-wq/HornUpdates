// Writes the candidate-inbox PR body as a checklist. Ticking a box and merging the PR
// asks the publish workflow to draft that story. Boxes already ticked in the current
// PR body (passed via PREVIOUS_BODY_FILE) stay ticked when the collector refreshes it.
import fs from 'node:fs/promises';

const MAX_LISTED = 30;
const inbox = JSON.parse(await fs.readFile(new URL('../data/ai-inbox.json', import.meta.url), 'utf8'));
const previous = process.env.PREVIOUS_BODY_FILE ? await fs.readFile(process.env.PREVIOUS_BODY_FILE, 'utf8').catch(() => '') : '';
const ticked = new Set([...previous.matchAll(/^- \[[xX]\] `([^`]+)`/gm)].map(m => m[1]));

const clean = s => String(s).replace(/[\r\n`[\]]+/g, ' ').trim();
// Primary sources first, then newest first.
const rank = c => (c.source_type === 'primary' ? 0 : 1);
const candidates = (inbox.candidates || [])
  .filter(c => c.status === 'candidate' && c.id && c.url)
  .sort((a, b) => rank(a) - rank(b) || String(b.discovered_at).localeCompare(String(a.discovered_at)));
const listed = [...candidates.filter(c => ticked.has(c.id)), ...candidates.filter(c => !ticked.has(c.id))].slice(0, MAX_LISTED);
const lines = listed.map(c => `- [${ticked.has(c.id) ? 'x' : ' '}] \`${c.id}\` — [${clean(c.title)}](${c.url}) · ${clean(c.source)}`);
const errors = (inbox.source_errors || []).map(e => `- ${clean(e.source)}: ${clean(e.error)}`);

const body = `<!-- hornupdates-inbox -->
**Tick the stories worth covering, then merge.** Merging starts the publish workflow: Claude drafts each ticked story and opens a separate **Publish** PR. Nothing goes live until you review and merge that one.

Merging with nothing ticked just saves the inbox.

${lines.length ? lines.join('\n') : '_No new candidates._'}
${candidates.length > MAX_LISTED ? `\n_${candidates.length - MAX_LISTED} older candidates not shown; they stay in \`data/ai-inbox.json\`._\n` : ''}${errors.length ? `\n<details><summary>Source errors (${errors.length})</summary>\n\n${errors.join('\n')}\n</details>\n` : ''}`;

const out = process.argv[2];
if (out) await fs.writeFile(out, body); else console.log(body);
