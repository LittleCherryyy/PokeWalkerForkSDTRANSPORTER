# Resident Wi-Fi integration: evidence and safety gate (2026-11-22)

## Scope
Design review only. No ROM/save modifications and no DSi test package.

## Verified in repository
- `core/bootstrap/retail/common/source/walker_hgss_net.c` deliberately leaves WCM/SOCL/SOC callable slots unresolved and `ready=0` until every required function is identified.
- `core/DIRECT-DSI-SYNC-V18.md` proposes ARM9 network ownership and ARM7 walker storage ownership, with Android TCP port 30821.
- Repository documentation explicitly says in-game wireless transfer has not been validated.

## Later local investigation (not verified in this repository)
Conversation history reports V104 ARM9 execution, V105 inconclusive stores, 65,536-byte virtual EEPROM work, and an overlay 13/74 lifetime conflict. These results require importing/reviewing the corresponding local source and logs before any implementation based on them.

## Next engineering gate
1. Identify the exact HGSS revision and overlay load/unload ranges; do not assume overlay 13 and menu overlay 74 coexist.
2. Locate Wi-Fi initialization/teardown ownership and whether required network code is resident in the main ARM9 image. Check symbol identity, calling convention, mode (ARM/Thumb), and lifetime.
3. Define a small nonblocking state machine (DISABLED -> INIT -> ASSOCIATING -> CONNECTED -> TRANSFERRING -> SHUTDOWN / ERROR), with bounded retries, explicit cancellation, and no calls while required code is unloaded.
4. Keep network disabled unless all entry points, data pointers, and safe scheduling conditions are proven. A gateway pointer alone is not sufficient.
5. Keep EEPROM writes and save transitions disabled until a reversible, integrity-checked protocol is proven in a disposable test environment.
6. Validate off-device with deterministic mocked transport and fault injection before requesting a single DSi test that can demonstrate real in-game transfer.

## Acceptance criteria for next code change
- No guessed addresses or ABI assumptions.
- Explicit overlay lifetime guard and fail-closed path.
- No modification of user saves.
- Reproducible host-side tests and build instructions.
- Preserve upstream credits and licensing.

## User test policy
Do not request more GDB, PING, or standalone homebrew tests. Request DSi/Android testing only when an actual in-game Pokémon transfer candidate is ready.
