# Device command contract

Commands are published on `<environment>/devices/<client_id>/command`, QoS 1.

## Version 1 (deployed on the whole fleet)

```json
{"schema_version": 1, "mode": "power_reference", "power_command_kw": 120.0}
```

- `power_command_kw`: kW, **positive = charge**, negative = discharge.
- Devices reject any command whose `schema_version` they do not support, and keep
  their last valid command.
- A device that receives no valid command for 60 s falls back to 0 kW.

## Evolving the contract

Devices are updated over weeks. A new version must be supported by the devices
**before** the server starts sending it.
