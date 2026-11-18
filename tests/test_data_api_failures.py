import pytest

from helpers import create_measurement, wait_for_final_status


@pytest.mark.mock_only
@pytest.mark.parametrize(
    "data_api",
    [
        pytest.param("malformed", id="tc11-malformed-response"),
        # assumption: the backend has a time limit for the Data API (the contract defines none)
        pytest.param("timeout", id="tc12-no-response"),
    ],
)
def test_tc11_tc12_data_api_failure_ends_failed_without_result(
    base_url, make_measurement, data_api
):
    measurement = make_measurement()

    measurement_id = create_measurement(base_url, measurement, data_api=data_api)

    final = wait_for_final_status(base_url, measurement_id)
    assert final["status"] == "failed"
    assert final["result"] is None