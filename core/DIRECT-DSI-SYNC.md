# Direct DSi Sync alpha (V14)

Goal: HGSS running under the modified nds-bootstrap talks to the Android Pokewalker app without opening Pokewalker-NDS.nds or another intermediary homebrew.

## Target topology

1. Android user enables an open 2.4 GHz hotspot manually.
2. DSi connects to that hotspot using DS-compatible Wi-Fi settings.
3. Android enables **Direct DSi sync** in Settings and listens on TCP 30821.
4. nds-bootstrap uses the DHCP gateway address (the phone) automatically; no IP entry is required.
5. After HGSS completes a virtual Pokewalker handoff, nds-bootstrap checks out the 64 KiB walker to Android.
6. For return, nds-bootstrap asks Android for the same session, writes and verifies the walker locally, then sends a CRC confirmation. Android only retires its active copy after that confirmation.

## V14 alpha implemented now

- Android foreground `DirectSyncService`, TCP port 30821.
- Compact binary protocol shared with bootstrap (`walker_directsync.h`).
- PUSH_TO_PHONE, PULL_FROM_PHONE, CONFIRM_RETURN and PING operations.
- 32-hex session binding, 36-hex trainer binding and CRC32 payload validation.
- Android profile/session validation and recovery snapshots.
- Android does not delete its active walker until the DSi confirms the stored CRC.
- `tools/directsync_mock_dsi.py` can act as a host-side test client.

## Not implemented yet in this alpha

The physical DSi in-game network bridge. HGSS runs in DS mode; its injected virtual Pokewalker code is ARM9-side while Wi-Fi hardware is ARM7-side. The existing standalone NDS companion can use DSWiFi because it owns both CPUs. The in-game bridge must instead be integrated into nds-bootstrap's persistent ARM7/cardengine and communicate with the existing WalkerControl/EEPROM area.

This is intentionally not faked by putting socket calls into `walker.c`: that code has no valid ARM7 DSWiFi core behind it while HGSS is running.

## Wire format

All multibyte numbers are big-endian.

- magic: 8 bytes `PWDSI001`
- version: 1 byte
- operation: 1 byte
- flags: 2 bytes
- payload length: 4 bytes
- CRC32: 4 bytes
- session: 32 ASCII bytes, NUL padded
- trainer binding: 36 ASCII bytes, NUL padded
- optional payload

Port: 30821.

## Android test

Enable Direct DSi sync in app Settings, then from a machine on the same hotspot/network:

```text
python tools/directsync_mock_dsi.py PHONE_IP ping
```

The mock also supports push, pull and confirmation once supplied with a valid `.walker`, session and trainer key.
