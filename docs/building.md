# Building the RETR0 client

## Requirements

| Item | Used for |
|---|---|
| Your original `real-racing-3-14-0-1.apk` | The input; SHA-256 `dcfe3788004444bd69e2fb839c18a973b488e94f46f1b818b6c005afdcad1d5f` (any other file is refused) |
| Python 3 | The build script (standard library only) |
| Android NDK 28 (`clang`, `ld.lld`, `llvm-objcopy`, `llvm-nm`, `llvm-readelf`) | Building and linking the ARM64 handlers (assembly + C) |
| Android build-tools 36 (`zipalign`, `apksigner`) | Aligning and signing the final APK |
| A debug keystore | `%USERPROFILE%\.android\debug.keystore` (created by Android Studio / the SDK); override with `--keystore` |

Java and APKTool are no longer needed (since 0.2.0 the redirect is part of the native patch).

## The build

```powershell
python patches\store_grant_patch\build_patch.py --apk <apk> --out build\apk `
    --ndk-bin <ndk llvm bin folder> --build-tools <build-tools 36 folder>
```

1. Checks the APK's SHA-256 and that the library's CRC matches.
2. Assembles `store_grant_patch.S`, compiles `retr0_redirect.c` and links both with `cave.ld` at the code cave
   `0x9876c8`, with every game address as a `--defsym`. Checks that `.text` is the only allocated section, that no
   symbol needs writable data, and that the code fits the cave (0x938 bytes).
3. Checks that the cave is all zeros and that **every hooked instruction is exactly the expected one**. Any
   difference stops the build.
4. Writes the handlers and the five hook branches, and fixes the library's zip CRC.
5. Zip-aligns (`-P 16`), signs a copy with the debug key and verifies the signature; writes `patch_data.json`.

| Output | Use |
|---|---|
| `rr3_14.0.1_retr0_client.apk` | The RETR0 client: swap into an existing install |
| `rr3_14.0.1_retr0_client_signed.apk` | The RETR0 client, debug-signed: for a new install |
| `patch_data.json` | Built cave bytes and hook words (input for a planned standalone patcher) |

The build is reproducible: the same original APK gives byte-identical outputs.

## Changing a patch

- Handlers: edit `store_grant_patch.S` (or `retr0_redirect.c` for the URL rewrite). Any new game address goes
  into `SYMS` in `build_patch.py`; a new
  hook needs its address, its expected first instruction (checked by the build) and a displaced-instruction
  trampoline in the handler.
- Verify a build by disassembling the hook sites and the cave (e.g. with capstone) before installing it.
- Read [how-the-client-is-patched.md](how-the-client-is-patched.md) first, especially the note on `x8` for functions
  returning C++ objects by value.
