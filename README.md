# fleet-commands

Service that sends, every 10 seconds, the current power setpoint of each site to
its control box over MQTT.

## Domain in one minute

- **Site**: a battery installed at a customer site and connected to the grid. A
  **control box** on site receives our commands and drives the battery.
- **Plan**: how much each site should charge or discharge, per quarter-hour,
  computed daily by an optimizer from market prices. It can be recomputed: the
  latest version wins.
- **Setpoint (command)**: the power a box must apply now, i.e. the plan of the
  current quarter-hour, clamped to the site power limits.
- **Sign**: positive = charge, negative = discharge. **Units**: MW in the
  database, kW in the commands.

## Where to look

| Topic | File |
|---|---|
| What a tick does | `run_tick` and the docstrings in [command_sender.py](src/fleet_commands/command_sender.py) |
| Tables and columns | [docs/schema.dbml](docs/schema.dbml) |
| Command format, agreed with the boxes | [docs/device-contract.md](docs/device-contract.md) |

## Not in this repository

The scheduler that calls `run_tick`, the database and MQTT clients (injected), the
optimizer that writes the plan, and telemetry ingestion.

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
```
