# RETR0 Client

**Patch sources and build scripts that turn your own copy of Real Racing 3 (Android 14.0.1) into the RETR0 client:
a client that talks to the [RETR0 Server](https://github.com/Tankonline/RETR0-Server) on your PC, with a few
preservation features added.**

> **No APK is published here, and none ever will be**: neither the original nor a patched one. A patched APK is still
> EA's game. Everything in this repository is independently written, and every build reads **your own** original
> APK (SHA-256 checked) and writes a new file next to it. See [DISCLAIMER.md](DISCLAIMER.md).

## What the client adds

| Feature | What it does | Docs |
|---|---|---|
| Built-in server redirect | Sends CloudCell and asset-CDN traffic to the RETR0 server (`127.0.0.1:8780`); no Frida, no time limit | [server-redirect](docs/features/server-redirect.md) |
| Special events | Grand Prix / Special Events open again (they only needed a working connection) | [special-events](docs/features/special-events.md) |
| Store preservation grants | BUY on a currency package or currency pack gives its contents through the game's own non-purchase reward path | [store-grants](docs/features/store-grants.md) |
| Player name | Enter Racing Code sets the name shown instead of "Guest" (Profile, race results) | [username](docs/features/username.md) |

## Build

You need: your original `real-racing-3-14-0-1.apk` (SHA-256 `dcfe3788004444bd69e2fb839c18a973b488e94f46f1b818b6c005afdcad1d5f`),
Python 3, Java with APKTool 3.0.3, the Android NDK 28 and build-tools 36.

```powershell
python patches\local_server_redirect\build_redirect_dex.py --apk <apk> --out build\apk --apktool <apktool_3.0.3.jar>
python patches\store_grant_patch\build_patch.py --apk <apk> --out build\apk `
    --ndk-bin <sdk>\ndk\28.2.13676358\toolchains\llvm\prebuilt\windows-x86_64\bin --build-tools <sdk>\build-tools\36.0.0
```

Outputs in `build\apk\`: `rr3_14.0.1_retr0_client.apk` (swap into an existing install, keeps data) and
`rr3_14.0.1_retr0_client_signed.apk` (debug-signed, for a new install). Details: [docs/building.md](docs/building.md).

## Install and play

With the [RETR0 Server](https://github.com/Tankonline/RETR0-Server): copy the built APKs into the server's
`server\client\apk\`, then `server\client.ps1 apply` and `server\play.cmd`. See [docs/installing.md](docs/installing.md).

## Repository layout

| Folder | Contents |
|---|---|
| [`patches/local_server_redirect/`](patches/local_server_redirect/) | `Redirect.smali` and the script that builds `classes2_redirect.dex` |
| [`patches/store_grant_patch/`](patches/store_grant_patch/) | `store_grant_patch.S` (ARM64 handlers: store grants, player name) and `build_patch.py` (builds the client APKs) |
| [`docs/`](docs/) | How the patching works, building, installing, one page per feature |

## Licence

Code: [MIT](LICENSE). Documentation: [CC BY 4.0](LICENSE-DOCS.md). Real Racing 3 is a trademark of Electronic Arts
Inc. This project is not affiliated with or endorsed by EA, Firemonkeys or Glu.
