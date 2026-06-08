# NVMeter-drivedb

Community-maintained database of USB / Thunderbolt enclosure quirks that
NVMeter uses to talk SMART to your external drives.

**License: CC0 1.0** — public domain. Use this in your own project, fork it,
sell it, no attribution required (though it's appreciated). The goal is a
shared commons of bridge-chip knowledge that benefits every tool.

## How it's structured

Each enclosure / bridge chip is one YAML file under `bridges/`. Example:

```yaml
# bridges/jms583.yaml
bridge: "JMicron JMS583"
vendor: "JMicron"
usb_ids:
  - "152d:0583"
smartctl_args: ["-d", "sat,16"]
verified_by:
  - "@your-handle"
notes: |
  Common in Orico M2PVC3-G20 and similar single-bay NVMe enclosures.
  Firmware <204.6 may fail to pass through Identify; update if SMART times out.
```

Schema lives in [`schema/bridge.schema.json`](schema/bridge.schema.json) and is
enforced by CI on every PR.

## I have a new enclosure to add

1. Plug in the enclosure.
2. Run:
   ```bash
   system_profiler SPUSBDataType | grep -B 2 -A 8 -i <your-enclosure-name>
   smartctl --scan
   for args in "" "-d sat" "-d sat,16" "-d sat,12" "-d jmb39x" "-d usbjmicron"; do
       echo "=== $args ===" ; smartctl $args -i /dev/diskN | head -10
   done
   ```
3. Whichever combination prints a real model / serial works. Copy the
   `smartctl` flags into a new file under `bridges/<short-name>.yaml`.
4. Open a PR. CI will validate the schema; a maintainer merges.

If shell isn't your thing, open an issue using the **"new enclosure"**
template instead and paste the outputs — someone else will turn it into YAML.

## Field reference

| Field | Required | Meaning |
|---|---|---|
| `bridge` | ✅ | Human-readable chip name, e.g. `"ASMedia ASM2362"` |
| `vendor` | | Chip vendor |
| `usb_ids` | ✅ | List of `vendor:product` USB IDs (lowercase hex) |
| `smartctl_args` | ✅ | Arg list to pass to `smartctl` before the device path |
| `verified_by` | | List of GitHub handles who tested this entry |
| `notes` | | Anything future maintainers should know (firmware quirks, etc.) |

## License of contributions

By submitting a PR you agree your contribution is released under CC0 1.0.
No CLA, no copyright assignment — just public domain data.
