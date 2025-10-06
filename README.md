# Prana BLE integration

Control your Prana recuperator directly from Home Assistant over Bluetooth Low Energy. 

## What you get
- Automatic discovery through Home Assistant Bluetooth or manual setup by MAC address
- Fan speed control for the main, intake, and exhaust blowers, including preset modes (auto, auto plus, night, boost)
- Air quality and comfort sensors: indoor/outdoor temperatures, humidity, pressure, CO₂, TVOC, and current speeds
- Device options as entities: mini heating, winter mode, flow lock, display mode, and brightness

## Install with HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dmamelin&repository=ha_prana_ble&category=Integration)

**Or manually add the repository to HACS:**
1. Open **HACS → ⋮ → Custom repositories** and enter
   `https://github.com/dmamelin/ha_prana_ble` with category `Integration`.
2. After HACS refreshes, search for **Prana BLE**, install it, and restart
   Home Assistant when prompted.

## Manual install
Download the source archive and copy the extracted files straight into your Home Assistant 
`custom_components/prana_ble` directory. Restart Home Assistant.

## Set up
1. When the recuperator is in range you will see a suggestion card in **Settings → Devices & Services** prompting you to add the Prana BLE device—accept it to start the flow.
2. If no suggestion appears, choose **Add integration**, search for **Prana BLE**, and follow the manual flow. Enter the BLE MAC address only if Home Assistant did not prefill it—the integration trims the advertised name automatically.
3. Set the maximum speed (default 5) and update interval (default 30 seconds). You can change these later from the integration options.

## Troubleshooting
- Ensure the Home Assistant host (or Bluetooth proxy) can maintain a stable BLE connection and that no other app is paired with the recuperator.
- For detailed logging add:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.prana_ble: debug
  ```
  Restart, reproduce the problem, then review **Settings → System → Logs**.
