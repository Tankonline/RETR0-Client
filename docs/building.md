# Building the RETR0 client

## Requirements

| Item | Used for |
|---|---|
| Your original `real-racing-3-14-0-1.apk` | The input; SHA-256 `dcfe3788004444bd69e2fb839c18a973b488e94f46f1b818b6c005afdcad1d5f` (any other file is refused) |
| Python 3 | Both build scripts (standard library only) |
| Java + APKTool 3.0.3 | Decoding and rebuilding the DEX code for the redirect |
| Android NDK 28 (`clang`, `ld.lld`, `llvm-objcopy`, `llvm-nm`) | Assembling and linking the ARM64 handlers |
| Android build-tools 36 (`zipalign`, `apksigner`) | Aligning and signing the final APK |
| A debug keystore | `%USERPROFILE%\.android\debug.keystore` (created by Android Studio / the SDK); override with `--keystore` |

## Step 1 · The redirect (`classes2_redirect.dex`)

```powershell
python patches\local_server_redirect\build_redirect_dex.py --apk <apk> --out build\apk --apktool <apktool_3.0.3.jar>
```

1. Checks the APK's SHA-256.
2. `apktool d -r` decodes the code (resources stay encoded) into `build\apk\smali_work\`.
3. Checks `HttpRequest.init`'s signature and its last instructions are exactly as expected, then inserts the
   `Redirect.rewrite` and `Redirect.finish` calls.
4. Adds `Redirect.smali`, runs `apktool b`, and copies `classes2.dex` out as `build\apk\classes2_redirect.dex`.

Decoding and rebuilding takes a few minutes.

## Step 2 · The native patch and the APKs

```powershell
python patches\store_grant_patch\build_patch.py --apk <apk> --out build\apk `
    --ndk-bin <ndk llvm bin folder> --build-tools <build-tools 36 folder>
```

1. Checks the APK's SHA-256 and that the library's CRC matches.
2. Assembles `store_grant_patch.S` and links it at the code cave `0x9876c8`, with every game address as a `--defsym`.
3. Checks that the cave is all zeros and that **every hooked instruction is exactly the expected one**. Any
   difference stops the build.
4. Writes the handlers and the four hook branches, and fixes the library's zip CRC.
5. If `classes2_redirect.dex` is in `--out`, swaps it in, zip-aligns (`-P 16`), signs a copy with the debug key and
   verifies the signature.

| Output | Use |
|---|---|
| `rr3_14.0.1_store_grant_test.apk` | Native patch only (for comparison) |
| `rr3_14.0.1_retr0_client.apk` | The RETR0 client: swap into an existing install |
| `rr3_14.0.1_retr0_client_signed.apk` | The RETR0 client, debug-signed: for a new install |

The build is reproducible: the same original APK gives byte-identical outputs.

## Changing a patch

- Handlers: edit `store_grant_patch.S`. Any new game address it calls goes into `SYMS` in `build_patch.py`; a new
  hook needs its address, its expected first instruction (checked by the build) and a displaced-instruction
  trampoline in the handler.
- Verify a build by disassembling the hook sites and the cave (e.g. with capstone) before installing it.
- Read [how-the-client-is-patched.md](how-the-client-is-patched.md) first, especially the note on `x8` for functions
  returning C++ objects by value.
