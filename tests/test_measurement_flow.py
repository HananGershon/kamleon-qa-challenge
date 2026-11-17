import requests

from helpers import wait_for_final_status


def test_tc01_identified_user_result_saved_under_their_name(base_url, make_measurement):
    measurement = make_measurement(identified=True)

    response = requests.post(f"{base_url}/api/v1/measurements", json=measurement, timeout=5)

    # assumption: 201 Created for a new measurement (the contract gives no status codes)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["status"] == "processing"

    final = wait_for_final_status(base_url, created["measurementId"])
    assert final["status"] == "completed"
    assert final["userId"] == measurement["userId"]
    assert final["deviceId"] == measurement["deviceId"]
    # The contract's result echoes the volume, which ties the result to this measurement.
    assert final["result"]["volume"] == measurement["sensorData"]["volume"]
    assert isinstance(final["result"]["hydration"], (int, float))


def test_tc02_anonymous_user_result_returned_not_linked(base_url, make_measurement):
    measurement = make_measurement(identified=False)

    response = requests.post(f"{base_url}/api/v1/measurements", json=measurement, timeout=5)

    assert response.status_code == 201, response.text
    created = response.json()
    assert created["status"] == "processing"

    final = wait_for_final_status(base_url, created["measurementId"])
    assert final["status"] == "completed"
    assert final["userId"] is None
    assert final["deviceId"] == measurement["deviceId"]
    assert final["result"]["volume"] == measurement["sensorData"]["volume"]
    assert isinstance(final["result"]["hydration"], (int, float))