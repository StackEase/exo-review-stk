"""Send each site's current setpoint to its control box every 10 seconds."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

logger = logging.getLogger(__name__)

COMMAND_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Site:
    id: int
    client_id: str
    max_charge_kw: float
    max_discharge_kw: float


class Publisher(Protocol):
    def publish(self, topic: str, payload: str, qos: int) -> None: ...


PLAN_QUERY = """
    SELECT DISTINCT ON (site_id) site_id, power_mw
    FROM plan
    WHERE delivery_start = %(quarter)s
    ORDER BY site_id, computed_at DESC
"""


def quarter_start(at: datetime) -> datetime:
    return at - timedelta(
        minutes=at.minute % 15, seconds=at.second, microseconds=at.microsecond
    )


def load_plan_mw(conn, quarter: datetime) -> dict[int, float]:
    """Latest plan version of every site for the quarter (MW, positive = charge)."""
    with conn.cursor() as cur:
        cur.execute(PLAN_QUERY, {"quarter": quarter})
        return {site_id: power_mw for site_id, power_mw in cur.fetchall()}


def compute_command_kw(plan_mw: float, site: Site) -> float:
    return plan_mw * 1000


def build_payload(command_kw: float) -> str:
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
    plan_mw = load_plan_mw(conn, quarter_start(now))
    for site in sites:
        command_kw = compute_command_kw(plan_mw.get(site.id, 0.0), site)
        publisher.publish(
            f"{environment}/devices/{site.client_id}/command",
            build_payload(command_kw),
            qos=1,
        )
