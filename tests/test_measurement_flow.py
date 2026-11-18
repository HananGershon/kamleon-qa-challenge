import copy

import pytest
import requests

from helpers import create_measurement, wait_for_final_status


def test_tc01_identified_user_result_saved_under_their_name(base_url, make_measurement):
    measurement = make_measurement(identified=True)

    measurement_id = create_measurement(base_url, measurement)

    final = wait_for_final_status(base_url, measurement_id)
    assert final["status"] == "completed"
    assert final["userId"] == measurement["userId"]
    assert final["deviceId"] == measurement["deviceId"]
    # The contract's result echoes the volume, which ties the result to this measurement.
    assert final["result"]["volume"] == measurement["sensorData"]["volume"]
    assert isinstance(final["result"]["hydration"], (int, float))


def test_tc02_anonymous_user_result_returned_not_linked(base_url, make_measurement):
    measurement = make_measurement(identified=False)

    measurement_id = create_measurement(base_url, measurement)

    final = wait_for_final_status(base_url, measurement_id)
    assert final["status"] == "completed"
    assert final["userId"] is None
    assert final["deviceId"] == measurement["deviceId"]
    assert final["result"]["volume"] == measurement["sensorData"]["volume"]
    assert isinstance(final["result"]["hydration"], (int, float))


def hydration_without_race(base_url, make_measurement, measurement):
    # The model belongs to the data team, so the expected hydration comes from the system
    # itself: the same readings, sent alone (assumption: the model is deterministic).
    reference = make_measurement()
    reference["sensorData"] = copy.deepcopy(measurement["sensorData"])
    final = wait_for_final_status(base_url, create_measurement(base_url, reference))
    assert final["status"] == "completed"
    return final["result"]["hydration"]


@pytest.mark.mock_only
@pytest.mark.parametrize(
    "identified",
    [
        pytest.param(True, id="tc03-identified-users"),
        pytest.param(False, id="tc04-anonymous-users"),
    ],
)
def test_tc03_tc04_reverse_order_results_stay_with_their_own_measurement(
    base_url, make_measurement, identified
):
    first = make_measurement(identified=identified, volume=40)
    second = make_measurement(identified=identified, volume=70, device_id=first["deviceId"])
    first_expected = hydration_without_race(base_url, make_measurement, first)
    second_expected = hydration_without_race(base_url, make_measurement, second)
    # Equal results would make a swap invisible.
    assert first_expected != second_expected

    # The first measurement's Data API call is slowed, so the second result comes back first.
    first_id = create_measurement(base_url, first, data_api="slow")
    second_id = create_measurement(base_url, second)

    second_final = wait_for_final_status(base_url, second_id)
    # Proves the race really happened: without it the test would check nothing.
    first_now = requests.get(f"{base_url}/api/v1/measurements/{first_id}", timeout=5)
    assert first_now.status_code == 200, first_now.text
    assert first_now.json()["status"] == "processing"
    first_final = wait_for_final_status(base_url, first_id)

    assert first_final["status"] == "completed"
    assert first_final["userId"] == first["userId"]
    assert first_final["result"]["volume"] == first["sensorData"]["volume"]
    assert first_final["result"]["hydration"] == first_expected

    assert second_final["status"] == "completed"
    assert second_final["userId"] == second["userId"]
    assert second_final["result"]["volume"] == second["sensorData"]["volume"]
    assert second_final["result"]["hydration"] == second_expected