// Run inside Codex node_repl with @oai/sky; no DOM injection or fake backend.
import * as fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { join } from 'node:path';

export class PackagedJourney {
  constructor(sky, app, root) {
    this.sky = sky; this.app = app; this.root = root;
    this.archive = join(root, 'complete-archive');
    this.evidence = { classification: 'NOT-A-GATE', app, root, stages: [] };
  }
  async control(action) {
    const id = randomUUID();
    await fs.writeFile(join(this.root, 'command.pending'), JSON.stringify({ id, action }));
    await fs.rename(join(this.root, 'command.pending'), join(this.root, 'command.json'));
    for (let i = 0; i < 450; i++) {
      let response;
      try { response = JSON.parse(await fs.readFile(join(this.root, 'response.json'), 'utf8')); }
      catch (e) { if (e.code !== 'ENOENT') throw e; }
      if (response?.id === id) { assert.equal(response.ok, true, response.error); return response.result; }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw Error(`Lifecycle helper timed out: ${action}`);
  }
  async state() { return this.sky.get_app_state({ app: this.app, disableDiff: true }); }
  async click(label) {
    const before = await this.state();
    const rows = before.text.split('\n').filter(row => row.trim().endsWith(`button ${label}`));
    assert.equal(rows.length, 1, `Expected one enabled button: ${label}`);
    await this.sky.click({ app: this.app, element_index: Number(rows[0].trim().match(/^\d+/)[0]) });
    return this.state();
  }
  async fill(label, value) {
    const before = await this.state();
    const row = before.text.split('\n').find(row => row.includes(`(settable) ${label}, Value:`));
    assert.ok(row, `Missing editable control: ${label}`);
    await this.sky.set_value({ app: this.app, element_index: Number(row.trim().match(/^\d+/)[0]), value });
    return this.state();
  }
  async record(name, extra = {}) {
    const state = await this.state();
    await fs.writeFile(join(this.root, `${name}.ax.txt`), state.text);
    if (state.screenshot) await fs.copyFile(new URL(state.screenshot.url), join(this.root, `${name}.png`));
    this.evidence.stages.push({ name, ...extra });
    await fs.writeFile(join(this.root, 'journey-evidence.json'), JSON.stringify(this.evidence, null, 2));
    return state;
  }
  async selectCreatedProject() {
    let state = await this.state();
    const row = state.text.split('\n').find(row => row.includes('pop up button Active project,'));
    assert.ok(row);
    if (row.endsWith('Value: New Project')) return;
    await this.sky.click({ app: this.app, element_index: Number(row.trim().match(/^\d+/)[0]) });
    state = await this.state();
    // Sort order is observed from the live menu, not an assumed element index.
    const options = state.text.split('\n').filter(line => /^\s+\d+ (?!menu)/.test(line));
    const index = options.findIndex(line => /(?:\(selected\) )?New Project$/.test(line));
    assert.ok(index >= 0, 'Recovered project absent from menu');
    await this.sky.press_key({ app: this.app, key: 'Home' });
    for (let i = 0; i < index; i++) await this.sky.press_key({ app: this.app, key: 'Down' });
    await this.sky.press_key({ app: this.app, key: 'Return' });
    state = await this.state();
    assert.match(state.text, /Active project, Value: New Project/);
  }
  async capture() {
    const bytes = await fs.readFile(join(this.app, 'Contents/MacOS/Tom Assist'));
    this.evidence.binary_sha256 = createHash('sha256').update(bytes).digest('hex');
    assert.match((await this.state()).text, /Local Release Console/);
    await this.click('＋ New project');
    await this.click('Quick capture decision');
    assert.match((await this.click('Ledger')).text, /Document user-gated workflow/);
    await this.record('01-capture');
    await this.click('Exchange');
    assert.match((await this.click('Prepare diagnostic packet')).text, /TOM_ASSIST_STATE/);
    const before = await this.control('snapshot');
    await this.click('Prepare diagnostic packet');
    const after = await this.control('snapshot');
    for (const key of ['tree_sha256','rgm_sha256','idempotency','settings','originals','demotions']) assert.deepEqual(after[key], before[key], `Preview changed ${key}`);
    assert.equal(before.engine_tick, 4707); assert.equal(before.rgm_tick, 0);
    await this.record('02-pure-packet', { before, after });
  }
  async commit() {
    await this.click('Mark diagnostic turn sent');
    this.response = 'The connected beam transfers force to both columns. '.repeat(32) + 'END-WP20-永久-🙂';
    await this.fill('Simulated provider response', this.response);
    const state = await this.click('Evaluate diagnostic response and commit');
    assert.match(state.text, /"result": "PASS"/);
    this.committed = await this.control('snapshot');
    assert.equal(this.committed.engine_tick, 4708);
    assert.equal(this.committed.rgm_tick, 4709);
    assert.equal(this.committed.receipts.length, 1);
    assert.equal(Object.keys(this.committed.idempotency).length, 1);
    assert.equal(this.committed.counts.turns, 2);
    assert.equal(this.committed.counts.response_evaluations, 1);
    assert.equal(this.committed.receipts[0].taught, true);
    assert.equal(this.committed.receipts[0].activated_branch_ids.length, 16);
    assert.equal(this.committed.originals.length, 1);
    assert.ok(this.committed.originals[0][2].endsWith(this.response));
    await this.record('03-commit', { snapshot: this.committed });
  }
  async backup() {
    await this.click('Settings');
    await this.fill('Recovery directory', this.archive);
    assert.match((await this.click('Export complete project archive')).text, /Complete archive saved:/);
    assert.match((await this.click('Verify recovery archive')).text, /Archive verified:/);
    assert.match((await this.click('Create complete project backup')).text, /Verified backup saved:/);
    const backups = (await fs.readdir(this.root)).filter(name => name.startsWith('complete-archive-backup-'));
    assert.equal(backups.length, 1);
    this.backupPath = join(this.root, backups[0]);
    await this.fill('Recovery directory', this.backupPath);
    assert.match((await this.click('Verify recovery archive')).text, /Archive verified:/);
    await this.record('04-complete-backup', { archive: this.archive, backup: this.backupPath });
  }
  async restart() {
    const lifecycle = await this.control('restart');
    await this.selectCreatedProject();
    assert.match((await this.click('Ledger')).text, /Document user-gated workflow/);
    assert.deepEqual(await this.control('snapshot'), this.committed);
    const replay = await this.control('replay');
    await this.record('05-cold-restart', { lifecycle, replay, snapshot: await this.control('snapshot') });
  }
  async recover() {
    const lifecycle = await this.control('fresh-recovery');
    await this.click('Settings');
    await this.fill('Recovery directory', this.archive);
    assert.match((await this.click('Verify recovery archive')).text, /Archive verified:/);
    assert.match((await this.click('Import verified recovery archive')).text, /Project recovered: New Project/);
    await this.selectCreatedProject();
    assert.match((await this.click('Ledger')).text, /Document user-gated workflow/);
    assert.deepEqual(await this.control('snapshot'), this.committed);
    await this.record('06-fresh-store-import', { lifecycle, snapshot: await this.control('snapshot') });
  }
  async finish() {
    const lifecycle = await this.control('restart');
    await this.selectCreatedProject();
    assert.match((await this.click('Ledger')).text, /Document user-gated workflow/);
    assert.deepEqual(await this.control('snapshot'), this.committed);
    const replay = await this.control('replay');
    await this.record('07-recovered-restart', { lifecycle, replay, snapshot: await this.control('snapshot') });
    this.evidence.build_verification = 'completed';
    await fs.writeFile(join(this.root, 'journey-evidence.json'), JSON.stringify(this.evidence, null, 2));
    await this.control('stop');
    return this.evidence;
  }
}
