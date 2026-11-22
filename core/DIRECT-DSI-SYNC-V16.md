# V16 — HGSS resident network resolver

This milestone moves Direct Sync transport to ARM9, where HGSS' NitroDWC/SOC code actually lives.

Implemented:
- `WalkerHgssNetApi` stored in the shared WalkerControl page.
- runtime scan for the repeated HGSS sequence `DWC_InitInetEx(config,2,1,20) -> DWC_SetAuthServer(2) -> DWC_ConnectInetAsync()`;
- requires two callers to resolve to the same targets before accepting the result;
- ARM9 Direct Sync transport unit with exact 88-byte V14 framing (`PWDSI001`, big-endian length/CRC) and a strict API gate;
- cardengine tick point outside IRQ context.

Not yet enabled:
- status/process/cleanup and SOC socket signatures. V16 refuses to call the network until those are positively resolved. No guessed retail addresses are used.

Why: calling NitroDWC from ARM7 is wrong; the resident HGSS socket stack is ARM9 code. ARM7 remains responsible only for durable `.walker` storage.
