"""Run the shipped card's dialog and service writes in Node's VM, in both locales."""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("language", ["de", "en"])
def test_card_settings_behavior(language):
    card = Path(__file__).resolve().parents[2] / (
        "custom_components/ecoflow_smart_charge/frontend/ecoflow-smart-charge-card.js"
    )
    script = r"""
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const [path, language] = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({HTMLElement: class {}, window: {}, customElements: {get: () => true}, assert});
vm.runInContext(fs.readFileSync(path, 'utf8'), context);
context.language = language;
vm.runInContext(`
(async () => {
const rendered = Object.create(EcoFlowSmartChargeCard.prototype);
rendered._language = language; rendered._config = {};
let html = '';
rendered.shadowRoot = {set innerHTML(v) {html = v;}, querySelectorAll: () =>
  [...html.matchAll(/id="([^"]+)"/g)].map(m => ({id:m[1], addEventListener() {}}))};
rendered._render();
assert.ok(html.includes(language === 'de' ? 'Mehr sparen' : 'Save more'));
assert.ok(html.includes(language === 'de' ? 'Akku schonen' : 'Protect battery'));
assert.ok(html.includes('aria-describedby="policy-description"'));
const c = Object.create(EcoFlowSmartChargeCard.prototype);
c._language = language;
const el = () => ({parent: {}, value: '', textContent: '', dataset: {}, checked: false, focus() {},
  closest() { return this.parent; }, showModal() {}, reportValidity() {return true;}});
c._refs = Object.fromEntries(['enabled','mode','settings_mode','charging_policy','policy-description',
  'info','card-error','feedback','cancel','dialog','form','save', ...EFS_FIELDS.map(([k]) => 'field-'+k)].map(k => [k, el()]));
c.shadowRoot = {querySelectorAll: () => []};
c._entities = {};
c._update = () => {};
const states = {'switch.master': {state:'off'}, 'select.mode': {state:'shadow'},
  'select.settings_mode': {state:'simple'}, 'select.charging_policy': {state:'balanced'}};
for (const [key] of EFS_FIELDS) states['number.'+key] = {state: key === 'minimum_net_saving_ct' ? '8.7' : key === 'minimum_price_advantage' ? '27.5' : '1', attributes: {min:0,max:100,step:0.1}};
c._entities = Object.fromEntries(Object.keys(states).map(k => [k,k]));
const calls = [];
c._hass = {states, callService: async (...args) => calls.push(args)};
c._open();
assert.equal(c._refs.settings_mode.value, 'simple');
assert.equal(c._refs['field-minimum_net_saving_ct'].hidden, true);
assert.equal(c._refs['field-minimum_net_saving_ct'].disabled, true);
assert.equal(c._refs['field-minimum_net_saving_ct'].parent.hidden, true);
assert.equal(c._refs.charging_policy.parent.hidden, false);
for (const [key] of EFS_FIELDS) {
  assert.equal(c._refs['field-' + key].parent.hidden, true);
  assert.equal(c._refs['field-' + key].disabled, true);
}
assert.match(c._refs['policy-description'].textContent, language === 'de' ? /geschätzt/ : /estimated/);
c._refs.charging_policy.value = 'protect_battery';
await c._save();
assert.equal(calls.length, 1);
assert.equal(calls[0][2].option, 'protect_battery');
calls.length = 0;
c._refs.settings_mode.value = 'advanced'; c._settingsVisibility();
assert.equal(c._refs['field-minimum_net_saving_ct'].hidden, false);
assert.equal(c._refs['field-minimum_net_saving_ct'].value, '8.7');
await c._save();
assert.equal(calls.length, 1);
assert.equal(calls[0][2].option, 'advanced');
assert.equal(c._refs.charging_policy.parent.hidden, true);
calls.length = 0;
c._refs['field-minimum_net_saving_ct'].value = '9.2';
await c._save();
assert.equal(calls.length, 1);
assert.equal(calls[0][0], 'number');
assert.equal(calls[0][2].value, 9.2);
calls.length = 0;
c._refs.settings_mode.value = 'simple'; c._settingsVisibility();
await c._save();
assert.equal(calls.length, 1);
assert.equal(calls[0][2].option, 'simple');
delete states['select.settings_mode'];
c._open();
assert.equal(c._refs.settings_mode.value, 'advanced');
assert.equal(c._refs['field-minimum_price_advantage'].value, '27.5');
})().catch(e => {throw e;});
`, context);
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps([str(card), language]),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
