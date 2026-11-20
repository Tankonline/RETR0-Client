## What and why

<!-- The feature or fix, and the evidence for the hook (log strings, addresses, disassembly). -->

## How it was verified

<!-- Build output, disassembly of the hook sites, emulator test and logcat lines. -->

## Checklist

- [ ] No APK, DEX, `.so`, keystore, assets or saves committed
- [ ] Builds from the original APK; hooked instructions are checked by the build script
- [ ] Hook sites and branch targets checked in the disassembly
- [ ] Tested on an emulator with a backup; saves verified if they could be affected
- [ ] Feature documented in `docs/features/` and CHANGELOG updated
