import time

import requests

FINAL_STATUSES = ("completed", "failed")

def create_measurement(base_url, measurement, data_api=None):
    # data_api: test-only header that makes the mock's fake Data API misbehave
    # (slow, malformed, timeout). A real backend ignores it.
    headers = {"X-Mock-Data-API": data_api} if data_api else {}
    response = requests.post(
        f"{base_url}/api/v1/measurements", json=measurement, headers=headers, timeout=5
    )
    # assumption: 201 Created for a new measurement (the contract gives no status codes)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["status"] == "processing"
    return created["measurementId"]


def wait_for_final_status(base_url, measurement_id, timeout=10, interval=0.5):
    # Processing is asynchronous: poll until the measurement leaves "processing".
    # A timeout, not a fixed sleep, so a stuck measurement fails clearly (TC-12).
    deadline = time.monotonic() + timeout
    while True:
        response = requests.get(f"{base_url}/api/v1/measurements/{measurement_id}", timeout=5)
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in FINAL_STATUSES:
            return body
        if time.monotonic() > deadline:
            raise AssertionError(
                f"{measurement_id} still '{body['status']}' after {timeout}s"
            )
        time.sleep(interval)