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
