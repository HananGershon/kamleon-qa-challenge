# Part 2 — Test design

Where a test has a matching opposite case, it's noted as "Also": the bad case is blocked, and the matching good case still gets through.

**Priority:** P1 = the core flow breaks, or the harm is silent and can't be undone (wrong person, data leak, wrong result). P2 = the harm is visible or can be undone. Within P1, the top 3 below set the order.

**TC-01 · Identified user → result saved under their name**
- **Risk:** an identified user's result isn't saved under their ID. The core promise of the product fails.
- **Scenario:** An identified user completes a valid measurement.
- **Expected:** The measurement ends `completed`, with a result, under that user's ID.
- **Level:** API
- **Priority:** P1
- **Dependencies:** Known test user, identified in a session · mocked Data API
- **Automate?** Yes — every PR + after deployment
- **Assumption:** identification (QR/RFID) isn't in the API contract; the test starts after it.

**TC-02 · Anonymous user → result returned, not linked to any user**
- **Risk:** an anonymous user gets no result, or their measurement is linked to someone's profile.
- **Scenario:** An anonymous user completes a valid measurement.
- **Expected:** The measurement ends `completed`, with a result, and no user ID (`userId` is null).
- **Level:** API
- **Priority:** P1
- **Dependencies:** Mocked Data API
- **Automate?** Yes — every PR + after deployment
- **Assumption:** anonymous measurements still have a session ID (the contract always shows one).

**TC-03 · Two identified users, results return in reverse order → each result under the right user**
- **Risk:** the backend attaches a late result to the wrong measurement, so a user gets someone else's health result.
- **Scenario:** Two identified users measure one after the other at the same device. The first user's result is delayed, so the second user's result returns first (race condition).
- **Expected:** Both measurements end `completed`, each with its own result under its own user ID. No swap.
- **Level:** API
- **Priority:** P1
- **Dependencies:** Two known test users, each identified in a session · mocked Data API that can delay one result and return a different value per measurement
- **Automate?** Yes — every PR

**TC-04 · Two anonymous users, results return in reverse order → each result on the right measurement**
- **Risk:** with no user ID to match on, results swap between anonymous measurements and the wrong result is shown.
- **Scenario:** Two anonymous users measure one after the other at the same device. The first user's result is delayed, so the second user's result returns first (race condition).
- **Expected:** Both measurements end `completed`, each with its own result, and no user ID on either. No swap.
- **Level:** API
- **Priority:** P1
- **Dependencies:** Mocked Data API that can delay one result and return a different value per measurement
- **Automate?** Yes — every PR

**TC-05 · Measurement sent for a user not identified in that session → rejected (session validation)**
- **Risk:** a measurement is saved under a user who wasn't at the device, corrupting their health history.
- **Scenario:** The device sends a measurement with a user ID that doesn't match the user identified in that session (e.g. the user identified at a different device).
- **Expected:** The measurement is rejected with an error and not created.
- **Level:** API
- **Priority:** P1
- **Dependencies:** A way to create an identified session (not in the API contract → contract gap) · known test users
- **Automate?** Yes — every PR, once the backend exposes a way to create a session (contract gap)
- **Assumption:** identification creates a backend session linking user + device. The task states the backend handles "user/session management" but not how.
- **Also:** a measurement for the user identified in that session → accepted.

**TC-06 · User accesses a measurement outside their permissions → access denied (authorization)**
- **Risk:** one user reads another person's health data by changing an ID — a leak that can't be undone.
- **Scenario:** A logged-in user requests a measurement outside their permissions, e.g. by changing the measurement ID in the URL.

| Logged in as | Measurement belongs to | Expected |
|---|---|---|
| Athlete A | Athlete B, same club | 403 |
| Staff, club X | Athlete, club Y | 403 |

- **Expected:** 403 Forbidden (or 404 by design), with no measurement data in the response.
- **Level:** API
- **Priority:** P1
- **Dependencies:** Login with user roles and customer organizations (not in the API contract → contract gap) · test users of each role in two organizations
- **Automate?** Yes — after every deployment to staging (needs a real login; the mock has none)
- **Assumption:** customer organizations (e.g. clubs) are isolated from each other; athletes see only their own data; staff see their own organization's athletes. The task names the customer types but not their permissions.
- **Also:** staff, club X → athlete, club X → allowed.

**TC-07 · No health data written to the logs → logs keep IDs only (privacy)**
- **Risk:** health values written to logs reach anyone with log access — a silent privacy leak.
- **Scenario:** A measurement runs through the backend with unique test values that can't appear in the logs by chance. The service logs are then searched for those values.
- **Expected:** No health values (sensor readings, hydration) and no personal details appear in the logs.
- **Level:** Component (backend service + its logs)
- **Priority:** P1
- **Dependencies:** Access to the service logs on staging · a test user and unique test values
- **Automate?** Yes — nightly on staging
- **Assumption:** the backend writes processing logs; which fields count as personal data is agreed with security.
- **Also:** technical IDs (measurement ID, device ID) are still in the logs, so failures stay traceable.

**TC-08 · Valid but clinically implausible readings → no result shown (data quality)**
- **Risk:** a degraded sensor's readings produce a confident but wrong hydration result that the user acts on.
- **Scenario:** The Data API receives readings that are within their allowed ranges but clinically implausible, as a degraded sensor could produce.
- **Expected:** The measurement ends `failed`; no hydration result is shown to the user.
- **Level:** Integration (backend + real Data API)
- **Priority:** P1
- **Dependencies:** A reference set of implausible readings, defined by the data team · plausibility thresholds set by the data team
- **Automate?** Yes — every PR to the Data API (code, model or thresholds)
- **Assumption:** an implausible result is reported as `failed` (the API contract has no data-quality field → contract gap). QA doesn't set the thresholds; it verifies they're enforced.
- **Also:** plausible readings from the same reference set → `completed` with a result.

**TC-09 · Data API update → same readings still give the same hydration result (regression)**
- **Risk:** a code or model update silently changes hydration results for every user.
- **Scenario:** Before a Data API update goes live, a fixed set of anonymized real readings is run through the new version. The results are compared with the results the current version gives for the same readings.
- **Expected:** Every hydration result is identical to the current version's result.
- **Level:** Component (Data API)
- **Priority:** P1
- **Dependencies:** A fixed set of anonymized readings with their saved results from the current version
- **Automate?** Yes — every PR to the Data API
- **Assumption:** the model gives the same result for the same readings every time (deterministic). When an update is meant to change results, the data team reviews and approves the new results as the new baseline. Accuracy against a lab reference dataset, within a tolerance set by the data team, is covered in the strategy.

**TC-10 · Invalid or incomplete measurement → rejected (input validation)**
- **Risk:** impossible or incomplete readings are stored and processed, producing a result built on bad data.
- **Scenario:** The device sends a measurement with a sensor value outside its valid range, an impossible timing (it ends before it starts), or an incomplete measurement (a value missing, or cut off before it finished).
- **Expected:** The measurement is rejected with an error and isn't created.
- **Level:** API
- **Priority:** P1
- **Dependencies:** Valid ranges and the minimum volume, set by the hardware/data team
- **Automate?** Yes — every PR
- **Assumption:** valid ranges and a minimum volume exist; the task doesn't define them (contract gap).
- **Also:** values exactly at the edges of the valid range → accepted (boundary values).

**TC-11 · Data API returns a malformed response → measurement `failed`, nothing stored (response validation)**
- **Risk:** the backend stores a broken Data API response as a real result and shows it to the user.
- **Scenario:** A user completes a valid measurement. The backend sends the readings to the Data API, which sends back a malformed or incomplete response.
- **Expected:** The measurement ends `failed`. No result is stored or shown to the user.
- **Level:** API
- **Priority:** P1
- **Dependencies:** A mocked Data API that can return a malformed response
- **Automate?** Yes — every PR
- **Assumption:** the backend checks the Data API's response before storing it; the task doesn't say how.
- **Also:** a well-formed response → `completed` (see TC-01 · Identified user → result saved under their name).

**TC-12 · Data API doesn't respond → measurement `failed`, not stuck in `processing` (timeout)**
- **Risk:** a measurement stays `processing` forever, and the user waits for a result that never comes.
- **Scenario:** A user completes a valid measurement. The backend sends the readings to the Data API, which never responds (down or too slow).
- **Expected:** Once the agreed time limit passes (including any retries), the measurement ends `failed`. It doesn't stay `processing` forever.
- **Level:** API
- **Priority:** P2
- **Dependencies:** A mocked Data API that can stay silent · the time limit, set by the backend/product team
- **Automate?** Yes — every PR
- **Assumption:** the backend has a time limit for the Data API; the task doesn't define it, nor whether the backend retries (contract gap).
- **Also:** the Data API responds within the limit → `completed` (see TC-01 · Identified user → result saved under their name).

**TC-13 · Device reconnects and sends its buffered measurements → each saved exactly once (idempotency)**
- **Risk:** buffered measurements are lost or saved twice after a reconnect, distorting history and team statistics.
- **Scenario:** A device goes offline, then reconnects and sends its buffered measurements, including one it already sent before losing the connection.
- **Expected:** Every buffered measurement is saved exactly once; the one already sent returns its original measurement ID.
- **Level:** API
- **Priority:** P2
- **Dependencies:** A rule for what counts as "the same measurement", agreed with the backend team
- **Automate?** Yes — every PR
- **Assumption:** the same measurement = same device + session + start time (the contract has no idempotency key → contract gap). On a resend the backend returns the original ID; a "duplicate" error (409) would also be acceptable — the task doesn't say.
- **Also:** two different measurements sent close together from the same device (two anonymous users one after the other) → both are saved.

**TC-14 · Identified user measures on a real device → the display shows their result (E2E)**
- **Risk:** each part works alone but not together, so the display shows no result or the wrong one.
- **Scenario:** On a real device, a user identifies, completes a measurement and waits for the result. Run once with a QR code and once with an RFID wristband.
- **Expected:** The display shows that user's result — the same result stored under their ID.
- **Level:** E2E (real device + display)
- **Priority:** P1
- **Dependencies:** A real device and display connected to staging · test users with a QR code and an RFID wristband
- **Automate?** No — manual before every release (needs physical hardware; a hardware-in-the-loop rig is a roadmap option)
- **Assumption:** the display shows who the result belongs to; the task doesn't describe what the display shows.
- **Also:** identification fails (unreadable QR code or unknown wristband) → an error is shown and nothing is saved under any user.

---

## Why these three first

They share what makes harm worst with health data: nobody notices it, and it can't be undone.

1. **TC-03 · Two identified users, results in reverse order → each under the right user.** A swapped result gives someone another person's health advice and corrupts both histories — and neither user can tell. The race is realistic: each device serves people back to back, and Data API response times vary.
2. **TC-06 · User accesses a measurement outside their permissions → access denied.** One changed ID exposes another person's health data; once read, it can't be taken back. With clubs and companies as clients, one leak can lose a whole customer, and health data is a special category under GDPR.
3. **TC-08 · Valid but clinically implausible readings → no result shown.** A degraded sensor can produce readings that are technically valid but clinically implausible. Input validation can't catch them, so the user gets a confident but wrong hydration result and may act on it.

Duplicates and timeouts rank lower (P2): a timeout is visible, and a duplicate can be found and removed. Neither puts a result on the wrong person.
