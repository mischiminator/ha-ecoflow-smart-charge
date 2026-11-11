"""The bundled dashboard card: served once, and fed by one service device per entry."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from test_config_flow import submit
from test_native import selection

from custom_components.ecoflow_smart_charge.const import CARD_URL, DOMAIN


async def test_card_is_served_and_loaded_on_every_frontend_page(hass):
    from custom_components.ecoflow_smart_charge import _register_card

    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    with patch("homeassistant.components.frontend.add_extra_js_url") as add:
        await _register_card(hass)
    (config,) = hass.http.async_register_static_paths.call_args.args[0]
    assert config.url_path == CARD_URL
    assert config.path.endswith("frontend/ecoflow-smart-charge-card.js")
    url = add.call_args.args[1]
    assert url.startswith(CARD_URL + "?v=") and len(url) > len(CARD_URL) + 3


async def test_card_registration_is_skipped_without_frontend(hass):
    from custom_components.ecoflow_smart_charge import _register_card

    hass.http = None
    await _register_card(hass)


def test_card_defines_its_element_and_uses_only_integration_keys():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "custom_components/ecoflow_smart_charge/frontend/ecoflow-smart-charge-card.js"
    ).read_text()
    assert "customElements.define(EFS_CARD" in source
    assert "const EFS_CARD = 'ecoflow-smart-charge-card'" in source
    # No hard-coded installation entities or helpers survive from the old card.
    for leftover in ("input_number.", "input_boolean.", "input_text.", "stream_ac_pro"):
        assert leftover not in source


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_entities_share_one_service_device_and_status_lists_batteries(hass):
    chosen = selection(hass, models=["Stream Ultra X", "Stream AC", "Unknown 9000"])
    devices = dr.async_get(hass)
    devices.async_update_device(chosen["battery_devices"][0], name_by_user="Ultra")
    result = await submit(hass, chosen)
    entry = result["result"]
    await hass.async_block_till_done()
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    (service,) = dr.async_entries_for_config_entry(devices, entry.entry_id)
    assert service.identifiers == {(DOMAIN, entry.entry_id)}
    assert service.entry_type is dr.DeviceEntryType.SERVICE
    assert {e.device_id for e in entities} == {service.id}
    assert all(e.translation_key for e in entities)
    status = next(e.entity_id for e in entities if e.translation_key == "status")
    attributes = hass.states.get(status).attributes
    assert attributes["batteries"][0]["name"] == "Ultra"
    assert [b["capacity_kwh"] for b in attributes["batteries"]] == [3.84, 1.92, None]
    assert [b["reserve_entity"] for b in attributes["batteries"]] == entry.data["reserve_entities"]
    assert attributes["price_window_entity"] == entry.data["price_window_entity"]
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "language,samples,correction,expected",
    [
        ("de", "2", "1", "Verbrauchsprofil: lernt noch (2/14) · PV-Korrektur: ×1,00"),
        ("de", "3", "0.92", "Verbrauchsprofil: bereit (3/14) · PV-Korrektur: ×0,92"),
        ("de", "14", "1", "Verbrauchsprofil: bereit (14/14) · PV-Korrektur: ×1,00"),
        ("de", "15", "1", "Verbrauchsprofil: bereit (15/14) · PV-Korrektur: ×1,00"),
        ("en", "2", "1", "Consumption profile: still learning (2/14) · PV correction: ×1.00"),
        ("en", "3", "0.92", "Consumption profile: ready (3/14) · PV correction: ×0.92"),
        ("de", "0", "unavailable", "Verbrauchsprofil: lernt noch (0/14) · PV-Korrektur: —"),
    ]
    + [
        ("de", value, None, "Verbrauchsprofil: — · PV-Korrektur: —")
        for value in (
            None,
            "unknown",
            "unavailable",
            "",
            " ",
            "NaN",
            "Infinity",
            "bad",
            "-1",
            "2.9",
            "3.1",
            True,
            3,
        )
    ],
)
def test_card_profile_footer(language, samples, correction, expected):
    """Execute the bundled JS with HA states, including missing and malformed counts."""
    import json
    import subprocess
    from pathlib import Path

    card = (
        Path(__file__).resolve().parents[2]
        / "custom_components/ecoflow_smart_charge/frontend/ecoflow-smart-charge-card.js"
    )
    script = """
const fs = require('node:fs');
const vm = require('node:vm');
const [path, language, samples, correction] = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({
  HTMLElement: class {}, window: {},
  customElements: {get: () => true},
});
vm.runInContext(fs.readFileSync(path, 'utf8'), context);
context.language = language;
context.states = {};
if (samples !== null) context.states['sensor.profile_samples'] = {state: samples};
if (correction !== null) context.states['sensor.pv_correction'] = {state: correction};
const result = vm.runInContext(`
  const card = Object.create(EcoFlowSmartChargeCard.prototype);
  card._language = language;
  card._hass = {states};
  card._profileFooter(EFS_TEXT[language]);
`, context);
process.stdout.write(result);
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps([str(card), language, samples, correction]),
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout == expected
