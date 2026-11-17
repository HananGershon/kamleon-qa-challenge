import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

# Same tests, any environment: point BASE_URL at staging to run them there.
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def api_is_reachable():
    # The README starts the mock in the background, so pytest may start before it is up.
    # Wait for it instead of failing every test with a connection error.
    deadline = time.monotonic() + 10
    while True:
        try:
            requests.get(BASE_URL, timeout=2)  # any HTTP answer, even 404, means it is up
            return
        except requests.ConnectionError:
            if time.monotonic() > deadline:
                pytest.exit(f"Can't reach {BASE_URL} - is the mock running?", returncode=1)
            time.sleep(0.5)


@pytest.fixture
def base_url():
    return BASE_URL


def unique_id(kind):
    # QA-TEST- prefix: lets a real environment find and purge test data.
    return f"QA-TEST-{kind}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def make_measurement():
    # The contract has no delete endpoint, so measurements can't be cleaned up.
    # Every measurement gets its own IDs instead; tests never see each other's data.
    def _make(identified=True, volume=250.0, device_id=None):
        completed = datetime.now(timezone.utc)
        return {
            "deviceId": device_id or unique_id("DEV"),
            "userId": unique_id("USR") if identified else None,
            "sessionId": unique_id("SES"),  # new session each time, or the resend rule returns an old measurement
            "startedAt": (completed - timedelta(seconds=60)).isoformat(),
            "completedAt": completed.isoformat(),
            "sensorData": {"volume": volume, "ph": 6.5, "temperature": 36.5},
        }

    return _make