# Contributing to RETR0 Client

Thanks for helping preserve Real Racing 3. Patching a game binary needs care, so contributions follow a few rules.

## Ground rules (non-negotiable)

- **Never commit an APK**, original or patched, or any DEX, `.so`, keystore, asset or save. CI refuses them.
- **Patches must build from the user's own original APK** (SHA-256 checked) and must not embed EA code or bytes
  beyond the few instructions a hook displaces.
- **No hidden network traffic:** the client may only talk to the RETR0 server on `127.0.0.1`.
- **No fake purchases:** grants use the game's own non-purchase reward path; no receipts, billing calls or purchase
  records.
- **No personal data** in code, docs or logs.

## Adding or changing a hook

1. Find the function from evidence (log string, UI text key, source-path string, RTTI) and **read its disassembly**,
   not just pseudocode: check the calling convention (e.g. `x8` for objects returned by value) and the first
   instruction.
2. Add the handler to `patches/store_grant_patch/store_grant_patch.S`:
   - run the displaced first instruction and branch back to `function + 4` when not acting;
   - save and restore every register you use that the caller expects preserved;
   - log a `RETR0 …` line through the game's logger.
3. Add every game address to `SYMS` in `build_patch.py`, and the hook's expected first instruction to the checks.
4. Build, then **disassemble the hook sites and the cave** (e.g. with capstone) to confirm every branch target.
5. Test on an emulator with a **backup** of the game data; after anything that could touch saves, verify the save files
   (magic, size, checksum) on a byte-exact copy.
6. Document the feature in `docs/features/` with evidence and a confidence label.

## Pull requests

- One feature or fix per pull request; describe the hook, the evidence and how it was verified.
- Fill in the checklist in the pull request template.
