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
const isEthiopia = c => ETHIOPIA_FIRST.includes(c.source);
const ethiopia = interleave(open.filter(isEthiopia));
const regional = interleave(open.filter(c => !isEthiopia(c)));
const candidates = [...ethiopia, ...regional];

// Ticked candidates always stay listed. About a third of the remaining slots go to
// Sudan, Somalia, South Sudan and regional outlets so they aren't crowded out; any
// slots one group can't fill go to the other.
const free = Math.max(0, MAX_LISTED - ticked.size);
const untickedEthiopia = ethiopia.filter(c => !ticked.has(c.id));
const untickedRegional = regional.filter(c => !ticked.has(c.id));
let regionalSlots = Math.min(untickedRegional.length, Math.round(free / 3));
const ethiopiaSlots = Math.min(untickedEthiopia.length, free - regionalSlots);
regionalSlots = Math.min(untickedRegional.length, free - ethiopiaSlots);
const keep = new Set([...candidates.filter(c => ticked.has(c.id)), ...untickedEthiopia.slice(0, ethiopiaSlots), ...untickedRegional.slice(0, regionalSlots)]);
const listedEthiopia = ethiopia.filter(c => keep.has(c));
const listedRegional = regional.filter(c => keep.has(c));
const listed = [...listedEthiopia, ...listedRegional];

const tags = c => [c.language && c.language !== 'English' ? c.language : '', /state/.test(c.source_kind || '') ? 'state media' : '', c.source_published || ''].filter(Boolean).join(', ');
const line = c => `- [${ticked.has(c.id) ? 'x' : ' '}] \`${c.id}\` — [${clean(c.title)}](${c.url}) · ${clean(c.source)}${tags(c) ? ` _(${tags(c)})_` : ''}`;
const lines = [
  ...(listedEthiopia.length ? ['**Ethiopia**', ...listedEthiopia.map(line)] : []),
  ...(listedRegional.length ? ['', '**Sudan, Somalia, South Sudan and the region**', ...listedRegional.map(line)] : [])
];
const errors = (inbox.source_errors || []).map(e => `- ${clean(e.source)}: ${clean(e.error)}`);

const body = `<!-- hornupdates-inbox -->
**Tick the stories for this week's Signal, then merge.** Ticks are kept when the collector refreshes this list, so you can tick through the week and merge when you're ready. Merging starts the publish workflow: Claude drafts the ticked stories into one Signal edition and opens a separate **Publish** PR. Nothing goes live until you review and merge that one.

For contested events, tick more than one side's coverage where you can.

Merging with nothing ticked just saves the inbox.

${lines.length ? lines.join('\n') : '_No new candidates._'}
${candidates.length > MAX_LISTED ? `\n_${candidates.length - MAX_LISTED} older candidates not shown; they stay in \`data/inbox.json\`._\n` : ''}${errors.length ? `\n<details><summary>Source errors (${errors.length})</summary>\n\n${errors.join('\n')}\n</details>\n` : ''}`;

const out = process.argv[2];
if (out) await fs.writeFile(out, body); else console.log(body);
