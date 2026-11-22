# Direct DSi Sync V18 — resident NitroWiFi pivot

V18 removes the dependency on NitroDWC overlay 0. The transport now targets the NitroWiFi WCM/SOCL stack that is resident in HGSS ARM9.

Key decisions:
- ARM7 remains storage/durability owner for the .walker file.
- ARM9 owns Wi-Fi association and TCP.
- WCM handles scan/open-AP association.
- SOCL/SOC handles DHCP and TCP to Android port 30821.
- Android IP is discovered from `gSoclGateway` after DHCP, so no IP entry is required.
- US HeartGold/SoulSilver fallback for `gSoclGateway` is 0x021D464C, as documented by the matching decomp.
- Network execution remains hard-gated until every WCM/SOCL/SOC function is positively resolved.

This is still source-stage development and not yet a DSi test build.
