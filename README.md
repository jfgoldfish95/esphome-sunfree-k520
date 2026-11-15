# esphome-sunfree-k520

The [esphome-sunfree-blinds](https://github.com/amasolov/esphome-sunfree-blinds)
ESPHome component (MIT, by @amasolov), based on upstream commit `ed90e40`,
with changes for Sunfree "Radio+" **K520** motors (as sold by Blinds2go).

All changes sit behind one option. With it off, the component behaves
exactly as upstream.

```yaml
external_components:
  - source: github://jfgoldfish95/esphome-sunfree-k520@v0.1.0
    components: [sunfree_blinds]

sunfree_blinds:
  id: sunfree_hub
  cc1101_id: cc1101_radio
  hub_id: "xxxxxxxx"
  k520_mode: true
  wake_preamble: 160ms      # optional, 100-300ms

cover:
  - platform: sunfree_blinds
    name: "Blind"
    motor_id: "xxxxxxxx"
    invert_position: true   # K520 counts 100 as fully open
```

## What `k520_mode` changes

Found by driving real K520 motors with a HackRF-based hub emulator.

- **Post-pairing handshake.** K520 motors send no status reports (position,
  battery) until the hub sends action `0x2A` then `0x2C`, as the original
  Tuya hub does after pairing. The component now queues both for each
  roller ID when a motor pairs to this hub.
- **Status on demand.** After the handshake, `0x2A` then `0x2C` makes even
  an idle motor report. `request_status` (service, poll queue and the
  public `request_status_all()`) uses that instead of a STOP poll.
- **`send_config` action type `handshake`** to resend it by hand.
- **Position from status byte 16** (current position). Byte 22 is the
  target, so during a move upstream reports where the blind is going.
- **Inverted covers.** K520 counts 100 as open. Use `invert_position: true`;
  the motor's opening/closing state is now swapped to match as well.

## Other changes (any motor)

- **`wake_preamble`**: length of the wake-up preamble before each command,
  100-300 ms (default 160 ms, as upstream). The HackRF emulator used
  250 ms on K520 motors; try that if sleeping motors don't respond.
- **Public `request_status_all()`**, e.g. for an `on_boot` refresh:

  ```yaml
  esphome:
    on_boot:
      priority: -100
      then:
        - delay: 30s
        - lambda: id(sunfree_hub).request_status_all();
  ```

- **Web page fixed.** Upstream's page at `/sunfree` was behind a
  `USE_WEBSERVER_BASE` define that current ESPHome no longer sets, so it
  never appeared. It now turns on whenever `web_server:` is in the config.

Other K520 differences that need no code change: commands must go out at
433.95 MHz (upstream already does), and the motors append one clear `00`
byte to ACKs, status reports and pairing responses, which the existing
length handling already copes with.

Status: builds for ESP32-S3 (ESPHome 2026.10); hardware test pending.

## Licence

MIT, as upstream. See `LICENSE`.
