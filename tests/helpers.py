import time

import requests

FINAL_STATUSES = ("completed", "failed")


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