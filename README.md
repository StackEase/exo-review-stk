# fleet-commands

Service that sends, every 10 seconds, the current power setpoint of each site to
its control box over MQTT.

- Setpoints come from the market schedule (`plan` table, MW, positive = charge).
- The command format is a contract with the devices: see
  [docs/device-contract.md](docs/device-contract.md).

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
```
