import copy

import pytest
import requests

from helpers import create_measurement

# assumption: the contract defines no error codes, so 400 and 422 both count as rejected
REJECTED = (400, 422)
MISSING = object()


@pytest.mark.parametrize(
    "section, field, value",
    [
        pytest.param("sensorData", "ph", 14.1, id="ph-above-scale"),
        pytest.param("sensorData", "volume", 0, id="zero-volume"),
        pytest.param("sensorData", "temperature", MISSING, id="sensor-value-missing"),
        pytest.param(None, "completedAt", MISSING, id="cut-off-before-completed"),
    ],
)
def test_tc10_invalid_or_incomplete_measurement_rejected(
    base_url, make_measurement, section, field, value
):
    valid = make_measurement()
    invalid = copy.deepcopy(valid)
    target = invalid[section] if section else invalid
    if value is MISSING:
        del target[field]
    else:
        target[field] = value

    response = requests.post(f"{base_url}/api/v1/measurements", json=invalid, timeout=5)
    assert response.status_code in REJECTED, response.text

    # No delete or list endpoint, so prove nothing was stored: the valid version of the
    # same measurement must be created as new (201), not returned as a resend (200).
    create_measurement(base_url, valid)


@pytest.mark.parametrize("ph", [0, 14], ids=["ph-0", "ph-14"])
def test_tc10_also_ph_at_scale_edges_accepted(base_url, make_measurement, ph):
    measurement = make_measurement()
    measurement["sensorData"]["ph"] = ph

    create_measurement(base_url, measurement)