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