# YM-S1-BES BLE Meter for Home Assistant

Custom integration for Yunmu/YM-S1-BES BLE meter sockets.

It reads meter data locally over BLE and does not depend on the original
WeChat Mini-App or the vendor cloud.

## Install

Copy this directory to Home Assistant:

```text
config/custom_components/ym_s1_bes
```

Restart Home Assistant.

## Requirements

Your ESPHome Bluetooth Proxy must support active connections:

```yaml
bluetooth_proxy:
  active: true
```

## Add Device

In Home Assistant:

```text
Settings -> Devices & services -> Add integration -> YM-S1-BES BLE Meter
```

For this device:

```text
MAC: 25:01:10:00:0B:D6
Advertised name: YUNMD60B00100125
```

The BLE address field can usually be left empty if Home Assistant has already
seen the device through Bluetooth or an ESPHome Bluetooth Proxy.

## Entities

Sensors:

- Power
- Energy
- Voltage
- Current
- Power factor
- Total time
- Amount
- Valid power

Buttons:

- Clear energy
- Clear time
- Clear amount
- Clear all

Numbers:

- Unit price
- Timing power

Virtual loads can be managed from the integration options. Each load is exposed
as a separate Home Assistant device with transient power, voltage, current, and
power factor sensors. Only the selected active load receives live values.
