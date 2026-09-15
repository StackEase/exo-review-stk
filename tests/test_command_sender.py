import json
from datetime import datetime, timezone

from fleet_commands.command_sender import Site, build_payload, compute_command_kw, quarter_start, run_tick

SITE = Site(id=1, client_id="BOX-0001", max_charge_kw=500.0, max_discharge_kw=500.0)
NOW = datetime(2026, 10, 25, 10, 7, 42, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params):
        self.query = query

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, plan_rows):
        self._plan_rows = plan_rows

    def cursor(self):
        return FakeCursor(self._plan_rows)


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, topic, payload, qos):
        self.messages.append((topic, json.loads(payload), qos))


def test_plan_is_converted_to_kw():
    assert compute_command_kw(0.3, SITE) == 300.0


def test_command_is_clamped_to_site_limit():
    assert compute_command_kw(0.8, SITE) == 500.0


def test_payload_follows_contract():
    assert json.loads(build_payload(120.0)) == {
        "schema_version": 1,
        "mode": "power_reference",
        "power_command_kw": 120.0,
    }


def test_quarter_start():
    assert quarter_start(NOW) == datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)


def test_tick_publishes_one_command_per_site():
    other = Site(id=2, client_id="BOX-0002", max_charge_kw=500.0, max_discharge_kw=500.0)
    publisher = FakePublisher()

    run_tick(FakeConn([(1, 0.1)]), publisher, [SITE, other], "prod", NOW)

    assert [(topic, msg["power_command_kw"]) for topic, msg, _ in publisher.messages] == [
        ("prod/devices/BOX-0001/command", 100.0),
        ("prod/devices/BOX-0002/command", 0.0),
    ]
