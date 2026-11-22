# Direct DSi Sync V17 — HGSS connection-state resolver

V17 extends the dynamic ARM9 resolver introduced in V16.

Implemented:
- repeated-pattern resolution of `DWC_CheckInet`, `DWC_GetInetStatus`, and `DWC_ProcessInet`;
- relationship-based resolution of `DWC_CleanupInet` from the retry path inside `DWC_GetInetStatus`;
- resolver readiness levels (`1=start trio`, `2=connection state complete`, `3=SOC complete`);
- strict SOC gate remains: no socket is opened until `SOC_Socket/Connect/Recv/Send/Close` are positively resolved.

The Android V14 protocol and TCP port 30821 are unchanged.

This is still a source/development milestone, not yet the SD-card test build.
