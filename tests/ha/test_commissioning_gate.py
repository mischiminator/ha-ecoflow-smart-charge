"""An operator-supplied native match is not independent commissioning proof."""

from datetime import UTC, datetime, timedelta

import pytest
from test_executor import rig

from custom_components.ecoflow_smart_charge import runtime as runtime_module


class FrozenDateTime:
    """Minimal deterministic clock facade for cutover freshness tests."""

    instant = datetime(2026, 1, 4, tzinfo=UTC)

    @classmethod
    def now(cls, _tz=None):
        return cls.instant

    @staticmethod
    def fromisoformat(value):
        return datetime.fromisoformat(value)


@pytest.mark.parametrize("ack", [None, False])
async def test_native_self_comparison_never_replaces_commissioning(ack):
    runtime, _, _, _, calls, _ = await rig()
    runtime.mode = "shadow"
    runtime.authorized = False
    kwargs = {} if ack is None else {"commissioning_confirmed": ack}
    with pytest.raises(ValueError, match="commissioning"):
        await runtime.async_request_cutover(confirmed=True, **kwargs)
    assert runtime.mode == "shadow" and not runtime.authorized and calls == []


async def test_changed_plan_invalidates_operator_comparison():
    runtime, _, _, _, calls, gate = await rig()
    runtime.mode = "shadow"
    runtime.authorized = False
    gate["allowed"] = False
    with pytest.raises(ValueError):
        await runtime.async_request_cutover(confirmed=True, commissioning_confirmed=True)
    assert runtime.mode == "shadow" and not runtime.authorized and calls == []


@pytest.mark.parametrize(
    ("age", "changed_field", "changed_value"),
    [
        pytest.param(1200, None, None, id="exactly-1200-seconds-old"),
        pytest.param(1201, None, None, id="older-than-1200-seconds"),
        pytest.param(0, "reason", "changed", id="changed-reason"),
        pytest.param(0, "profile_valid", False, id="changed-profile-validity"),
        pytest.param(0, "advantage", 999.0, id="changed-advantage"),
        pytest.param(0, "net_saving", 999.0, id="changed-net-saving"),
        pytest.param(0, "allowed", False, id="changed-allowed"),
    ],
)
async def test_cutover_rejects_expired_or_changed_recorded_comparison(
    monkeypatch, age, changed_field, changed_value
):
    """A cutover must retain shadow mode without issuing device calls."""
    runtime, _, _, _, calls, gate = await rig()
    expected = {
        "allowed": True,
        "reason": "economical",
        "profile_valid": True,
        "advantage": 10.0,
        "net_saving": 5.0,
    }
    gate.update(expected)
    runtime.mode = "shadow"
    runtime.authorized = False
    await runtime.async_record_comparison(expected)
    assert runtime.comparison is not None

    runtime.comparison["at"] = (FrozenDateTime.instant - timedelta(seconds=age)).isoformat()
    if changed_field:
        gate[changed_field] = changed_value
    monkeypatch.setattr(runtime_module, "datetime", FrozenDateTime)

    with pytest.raises(ValueError, match="fresh unchanged comparison"):
        await runtime.async_request_cutover(confirmed=True, commissioning_confirmed=True)

    assert runtime.mode == "shadow"
    assert not runtime.authorized
    assert calls == []


async def test_explicit_external_commissioning_ack_with_unchanged_plan():
    runtime, _, _, _, calls, _ = await rig()
    runtime.mode = "shadow"
    runtime.authorized = False
    await runtime.async_request_cutover(confirmed=True, commissioning_confirmed=True)
    assert runtime.mode == "active" and runtime.authorized and calls == []
