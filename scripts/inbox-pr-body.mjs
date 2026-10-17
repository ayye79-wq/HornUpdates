// Writes the candidate-inbox PR body as a checklist. Ticking boxes and merging the PR
// asks the publish workflow to draft those stories into the next Signal edition. Boxes already ticked in the current
// PR body (passed via PREVIOUS_BODY_FILE) stay ticked when the collector refreshes it.
import fs from 'node:fs/promises';

const MAX_LISTED = 40;
const inbox = JSON.parse(await fs.readFile(new URL('../data/inbox.json', import.meta.url), 'utf8'));
const previous = process.env.PREVIOUS_BODY_FILE ? await fs.readFile(process.env.PREVIOUS_BODY_FILE, 'utf8').catch(() => '') : '';
const ticked = new Set([...previous.matchAll(/^- \[[xX]\] `([^`]+)`/gm)].map(m => m[1]));

const clean = s => String(s).replace(/[\r\n`[\]]+/g, ' ').trim();
// Ethiopia-focused outlets first; within each group take one candidate per outlet in
// turn so no single source (especially state media) crowds out the rest.
const ETHIOPIA_FIRST = ['The Reporter Ethiopia', 'Ethiopia Insight', 'BBC Amharic', 'BBC Afaan Oromoo', 'BBC Tigrinya', 'The Guardian (Ethiopia)', 'Ethiopian News Agency', 'Fana Media Corporation', 'ReliefWeb (Ethiopia)'];
function interleave(list) {
  const queues = new Map();
  for (const c of list) queues.set(c.source, [...(queues.get(c.source) || []), c]);
  const out = [];
  while ([...queues.values()].some(q => q.length)) for (const q of queues.values()) if (q.length) out.push(q.shift());
  return out;
}
const open = (inbox.candidates || []).filter(c => c.status === 'candidate' && c.id && c.url);
const candidates = [...interleave(open.filter(c => ETHIOPIA_FIRST.includes(c.source))), ...interleave(open.filter(c => !ETHIOPIA_FIRST.includes(c.source)))];
const listed = [...candidates.filter(c => ticked.has(c.id)), ...candidates.filter(c => !ticked.has(c.id))].slice(0, MAX_LISTED);
const tags = c => [c.language && c.language !== 'English' ? c.language : '', /state/.test(c.source_kind || '') ? 'state media' : '', c.source_published || ''].filter(Boolean).join(', ');
const lines = listed.map(c => `- [${ticked.has(c.id) ? 'x' : ' '}] \`${c.id}\` — [${clean(c.title)}](${c.url}) · ${clean(c.source)}${tags(c) ? ` _(${tags(c)})_` : ''}`);
const errors = (inbox.source_errors || []).map(e => `- ${clean(e.source)}: ${clean(e.error)}`);

const body = `<!-- hornupdates-inbox -->
**Tick the stories for this week's Signal, then merge.** Ticks are kept when the collector refreshes this list, so you can tick through the week and merge when you're ready. Merging starts the publish workflow: Claude drafts the ticked stories into one Signal edition and opens a separate **Publish** PR. Nothing goes live until you review and merge that one.

For contested events, tick more than one side's coverage where you can.

Merging with nothing ticked just saves the inbox.

${lines.length ? lines.join('\n') : '_No new candidates._'}
${candidates.length > MAX_LISTED ? `\n_${candidates.length - MAX_LISTED} older candidates not shown; they stay in \`data/inbox.json\`._\n` : ''}${errors.length ? `\n<details><summary>Source errors (${errors.length})</summary>\n\n${errors.join('\n')}\n</details>\n` : ''}`;

const out = process.argv[2];
if (out) await fs.writeFile(out, body); else console.log(body);
