from tests.conftest import HB


def register(client, device_id="device-01", name="Lab Device 01"):
    return client.post("/devices", json={"id": device_id, "name": name})


# --- registration ---
def test_register_device(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == "device-01"
    assert body["status"] == "OFFLINE"          # no heartbeat yet
    assert body["last_heartbeat"] is None


def test_register_duplicate_returns_409(client):
    register(client)
    assert register(client).status_code == 409


def test_register_validation(client):
    assert client.post("/devices", json={"id": "", "name": "x"}).status_code == 422
    assert client.post("/devices", json={"id": "bad id!", "name": "x"}).status_code == 422
    assert client.post("/devices", json={"id": "ok"}).status_code == 422


# --- heartbeat ---
def test_heartbeat_marks_online_and_stores_fields(client):
    register(client)
    r = client.post("/devices/device-01/heartbeat", json={**HB, "cpu_usage": 42, "signal_strength": -71})
    assert r.status_code == 200
    d = client.get("/devices/device-01").json()
    assert d["status"] == "ONLINE"
    assert d["last_heartbeat"] == "2026-09-21T10:30:00Z"
    assert d["cpu_usage"] == 42
    assert d["signal_strength"] == -71


def test_heartbeat_unknown_device_returns_404(client):
    assert client.post("/devices/nope/heartbeat", json=HB).status_code == 404


def test_heartbeat_validation(client):
    register(client)
    assert client.post("/devices/device-01/heartbeat", json={"status": "OK"}).status_code == 422
    assert client.post("/devices/device-01/heartbeat", json={**HB, "timestamp": "garbage"}).status_code == 422
    assert client.post("/devices/device-01/heartbeat", json={**HB, "cpu_usage": 150}).status_code == 422


# --- 30 second rule ---
def test_online_within_30s(client, clock):
    register(client)
    client.post("/devices/device-01/heartbeat", json=HB)
    clock.advance(29)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_online_at_exactly_30s_boundary(client, clock):
    register(client)
    client.post("/devices/device-01/heartbeat", json=HB)
    clock.advance(30)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_offline_after_30s(client, clock):
    register(client)
    client.post("/devices/device-01/heartbeat", json=HB)
    clock.advance(30.001)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"


def test_device_returns_online_after_new_heartbeat(client, clock):
    register(client)
    client.post("/devices/device-01/heartbeat", json=HB)
    clock.advance(60)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"
    client.post("/devices/device-01/heartbeat", json=HB)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_device_timestamp_does_not_affect_status(client):
    # A device with a wrong/old clock is still ONLINE: liveness uses server receive time.
    register(client)
    client.post("/devices/device-01/heartbeat", json={"timestamp": "2020-01-01T00:00:00Z", "status": "OK"})
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


# --- list / detail / summary ---
def test_get_unknown_device_returns_404(client):
    assert client.get("/devices/nope").status_code == 404


def test_list_and_status_filter(client, clock):
    for i in (1, 2, 3):
        register(client, f"device-0{i}", f"D{i}")
    client.post("/devices/device-01/heartbeat", json=HB)
    clock.advance(20)
    client.post("/devices/device-02/heartbeat", json=HB)
    clock.advance(15)  # device-01 is 35s old, device-02 is 15s old, device-03 never seen
    assert len(client.get("/devices").json()) == 3
    assert [d["id"] for d in client.get("/devices?status=ONLINE").json()] == ["device-02"]
    assert {d["id"] for d in client.get("/devices?status=OFFLINE").json()} == {"device-01", "device-03"}
    assert client.get("/devices?status=BOGUS").status_code == 422


def test_summary(client, clock):
    assert client.get("/summary").json() == {"total": 0, "online": 0, "offline": 0}
    for i in (1, 2, 3):
        register(client, f"device-0{i}", f"D{i}")
    for i in (1, 2):
        client.post(f"/devices/device-0{i}/heartbeat", json=HB)
    assert client.get("/summary").json() == {"total": 3, "online": 2, "offline": 1}
    clock.advance(31)
    assert client.get("/summary").json() == {"total": 3, "online": 0, "offline": 3}