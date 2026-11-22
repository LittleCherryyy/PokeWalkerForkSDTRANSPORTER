# V15 Direct DSi Sync — ARM7 bridge milestone

This milestone adds the durable handoff state machine inside nds-bootstrap.

## What is implemented

- `WalkerControl` now contains a Direct DSi bridge block.
- The virtual Pokéwalker never performs network I/O from ARM9.
- ARM7 first writes and physically verifies all dirty `.walker` sectors.
- Only after a durable commit does it queue `PUSH_READY` for Android.
- The queue carries CRC32 and a 32-hex session token compatible with the V14 Android protocol.
- VBlank advances a non-blocking transport state machine.
- Pull/confirm states are defined so return can be atomic: receive -> durable SD write -> confirm Android.
- The radio backend is an explicit interface with weak no-op functions. This source tree is safe before Wi-Fi is linked.

## What is NOT implemented yet

The actual DS-mode Wi-Fi transport is not linked yet. A stock HGSS ARM7 already owns timers/IRQ/audio and DSWifi requires both ARM7 and ARM9 components. The next milestone must choose and validate one of these on physical DSi:

1. inject a minimal DSWifi/lwIP client and coordinate its ARM9 half; or
2. reuse HGSS/NitroSDK wireless services through located functions.

V15 therefore does **not** claim that a physical DSi can transfer to Android yet. It is the state/transaction bridge required before enabling the radio.

## Safety invariant

No phone checkout is offered until the `.walker` bytes are durably committed to SD. Network failure leaves the local walker intact.
