<p align="center">
  <img src=".github/assets/banner.svg" alt="RETR0 Client" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Tankonline/RETR0-Client/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Tankonline/RETR0-Client/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Code: MIT" src="https://img.shields.io/badge/code-MIT-3ddc97"></a>
  <a href="LICENSE-DOCS.md"><img alt="Docs: CC BY 4.0" src="https://img.shields.io/badge/docs-CC%20BY%204.0-b7a8ff"></a>
  <img alt="Target: arm64-v8a, any CPU with the RETR0 link" src="https://img.shields.io/badge/target-arm64--v8a%20%C2%B7%20any%20CPU%20(link)-7c5cff">
  <img alt="Game: RR3 14.0.1" src="https://img.shields.io/badge/game-RR3%2014.0.1%20(Android)-ff7a18">
  <img alt="No APKs" src="https://img.shields.io/badge/APKs%20in%20repo-none-555">
</p>

<p align="center">
  <b>Turns your own copy of Real Racing 3 (Android 14.0.1) into the RETR0 client</b>: a client that talks to the
  <a href="https://github.com/Tankonline/RETR0-Server">RETR0 Server</a> on your PC, with preservation features added.
</p>

<p align="center">
  <a href="docs/building.md"><b>Build</b></a> ·
  <a href="docs/installing.md"><b>Install</b></a> ·
  <a href="docs/how-the-client-is-patched.md"><b>How it works</b></a> ·
  <a href="https://github.com/Tankonline/RETR0-Server"><b>RETR0 Server</b></a> ·
  <a href="CHANGELOG.md"><b>Changelog</b></a>
</p>

> [!IMPORTANT]
> **No APK is published here, and none ever will be**, neither original nor patched: a patched APK is still EA's game.
> Every build reads **your own** original APK (SHA-256 checked) and writes a new file next to it.

---

## Features

| | Feature | What it does |
|:---:|---|---|
| 🔌 | [**Built-in server redirect**](docs/features/server-redirect.md) | CloudCell and asset-CDN traffic goes to the RETR0 server (`127.0.0.1:8780`). No Frida, no time limit; every other host is untouched |
| 📶 | [**RETR0 link (LAN)**](docs/features/lan-link.md) | Play on another device on your Wi-Fi: the game finds the RETR0 server on your home network by itself. Any CPU type |
| 🏁 | [**Special events**](docs/features/special-events.md) | Grand Prix / Special Events open again: they only needed a working connection |
| 💰 | [**Store preservation grants**](docs/features/store-grants.md) | BUY on a currency package or pack gives its contents through the game's own non-purchase reward path, with amounts from the game's catalogue |
| 🏷️ | [**Player name**](docs/features/username.md) | Enter Racing Code sets the name shown instead of "Guest" on Profile and in race results; an optional data patch renames the button to "Change Username (Restart Required)" |

## How the patch works

```mermaid
flowchart TB
    A["Your original APK<br/>(SHA-256 checked)"] --> C["build_patch.py<br/>store_grant_patch.S + retr0_redirect.c (NDK clang)<br/>linked by cave.ld at the code cave 0x9876c8"]
    C --> D["verify cave is empty and every hooked<br/>instruction is the expected one"]
    D --> E["write handlers + 5 hook branches<br/>fix the library's zip CRC"]
    E --> F["zipalign · debug-sign"]
    F --> G["rr3_14.0.1_retr0_client.apk<br/>rr3_14.0.1_retr0_client_signed.apk"]
```

| Hook | Game function | Feature |
|---|---|---|
| `0xb8d6e4` | `NimbleMTX::PurchaseStoreProduct` | Store grants: currency packages |
| `0x13ef7e8` | `PackManager` pack purchase | Store grants: currency packs |
| `0x135e944` | Player-name function | Player name |
| `0x1516b1c` | Racing-code submit | Player name |
| `0x1ce350c` | Native wrapper of Java `HttpRequest.init` | Server redirect |

The base build changes only `lib/arm64-v8a/libRealRacing3.so`; the Java code is untouched (since 0.2.0). The
optional LAN build ([RETR0 link](docs/features/lan-link.md)) adds one call in `classes2.dex` and a new `classes6.dex`.

Details, including lessons learned (like the `x8` return register): **[docs/how-the-client-is-patched.md](docs/how-the-client-is-patched.md)**.

## Build

You need your original `real-racing-3-14-0-1.apk`
(SHA-256 `dcfe3788004444bd69e2fb839c18a973b488e94f46f1b818b6c005afdcad1d5f`), Python 3, the Android NDK 28 and
build-tools 36. (Java and APKTool are no longer needed.)

```powershell
python patches\store_grant_patch\build_patch.py --apk <apk> --out build\apk `
    --ndk-bin <sdk>\ndk\28.2.13676358\toolchains\llvm\prebuilt\windows-x86_64\bin --build-tools <sdk>\build-tools\36.0.0
```

| Output | Use |
|---|---|
| `build\apk\rr3_14.0.1_retr0_client.apk` | Swap into an existing install: keeps your progress |
| `build\apk\rr3_14.0.1_retr0_client_signed.apk` | Debug-signed, for a new install |

Builds are **reproducible**: the same original APK gives byte-identical outputs. More: [docs/building.md](docs/building.md).

## Install and play

With the [RETR0 Server](https://github.com/Tankonline/RETR0-Server): copy the APKs into `server\client\apk\`, then

```powershell
server\client.ps1 apply          # in-place swap, keeps your data
server\retr0_server.cmd start -WithSync
server\play.cmd
```

See [docs/installing.md](docs/installing.md). For a phone or tablet on your Wi-Fi, use the LAN build and the
server's [LAN mode](https://github.com/Tankonline/RETR0-Server/blob/main/docs/features/lan-mode.md).

## Repository layout

```
patches/store_grant_patch/       store_grant_patch.S (ARM64 handlers), retr0_redirect.c, cave.ld, build_patch.py
patches/retr0_link/              Redirect.java + Link.java + build_link.py (RETR0 link, Wi-Fi connection)
patches/ui_text/                 retr0_gui_patch.py (button text, a game-data patch; used by client.ps1 ui-text)
patches/local_server_redirect/   Redirect.smali + build_redirect_dex.py (0.1.0 Java redirect, reference only)
docs/                            how it works, building, installing, one page per feature
```

## Legal

Code is [MIT](LICENSE); documentation is [CC BY 4.0](LICENSE-DOCS.md). Read the [disclaimer](DISCLAIMER.md).
Real Racing 3 is a trademark of Electronic Arts Inc. This project is not affiliated with or endorsed by EA, Firemonkeys
or Glu.
