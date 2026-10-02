"""Send each site's current setpoint to its control box.

``run_tick`` is called every 10 seconds by a scheduler that is not part of this
repository. Each call reads the market plan of the current quarter-hour and
publishes one absolute power command per site.

Conventions: power is positive when the battery charges and negative when it
discharges. The database stores MW, the commands sent to the boxes use kW.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

logger = logging.getLogger(__name__)

COMMAND_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Site:
    """A battery site driven by one control box.

    :param id: site identifier, as in the ``plan`` table.
    :param client_id: control box identifier, used in the MQTT topic.
    :param max_charge_kw: maximum charging power, in kW (> 0).
    :param max_discharge_kw: maximum discharging power, in kW (> 0).
    """

    id: int
    client_id: str
    max_charge_kw: float
    max_discharge_kw: float


class Publisher(Protocol):
    """MQTT client used to send commands, provided by the caller."""

    def publish(self, topic: str, payload: str, qos: int) -> None: ...


PLAN_QUERY = """
    SELECT DISTINCT ON (site_id) site_id, power_mw
    FROM plan
    WHERE delivery_start = %(quarter)s
    ORDER BY site_id, computed_at DESC
"""


def quarter_start(at: datetime) -> datetime:
    """Return the start of the quarter-hour containing ``at``."""
    return at - timedelta(
        minutes=at.minute % 15, seconds=at.second, microseconds=at.microsecond
    )


def load_plan_mw(conn, quarter: datetime) -> dict[int, float]:
    """Load the latest plan version of every site for a quarter-hour.

    :param conn: PostgreSQL connection (psycopg2, default transactional mode).
    :param quarter: start of the quarter-hour (timezone-aware).
    :returns: planned power by site id, in MW (positive = charge). Sites without
        a plan for this quarter-hour are absent.
    """
    with conn.cursor() as cur:
        cur.execute(PLAN_QUERY, {"quarter": quarter})
        return {site_id: power_mw for site_id, power_mw in cur.fetchall()}


def compute_command_kw(plan_mw: float, site: Site) -> float:
    """Convert a planned power to the command sent to the box.

    :param plan_mw: planned power, in MW (positive = charge).
    :param site: the site, for its power limits.
    :returns: command in kW, clamped to ``[-max_discharge_kw, max_charge_kw]``.
    """
    command_kw = plan_mw * 1000
    return min(max(command_kw, -site.max_discharge_kw), site.max_charge_kw)


def build_payload(command_kw: float) -> str:
    """Serialize a command, following the device contract (docs/device-contract.md)."""
    return json.dumps(
        {
            "schema_version": COMMAND_SCHEMA_VERSION,
            "mode": "power_reference",
            "power_command_kw": command_kw,
        }
    )


def run_tick(
    conn, publisher: Publisher, sites: list[Site], environment: str, now: datetime
) -> None:
    """Send the current command to every site.

    A site without a plan for the current quarter-hour receives 0 kW. Commands are
    absolute values: sending the same command twice is harmless.

    :param conn: PostgreSQL connection (psycopg2).
    :param publisher: MQTT client.
    :param sites: sites to command.
    :param environment: ``dev``, ``staging`` or ``prod``, used in the MQTT topic.
    :param now: current time (timezone-aware).
    """
    plan_mw = load_plan_mw(conn, quarter_start(now))
    for site in sites:
        command_kw = compute_command_kw(plan_mw.get(site.id, 0.0), site)
        publisher.publish(
            f"{environment}/devices/{site.client_id}/command",
            build_payload(command_kw),
            qos=1,
        )
