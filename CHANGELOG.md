# Changelog

All notable changes to the RETR0 Client patches. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-20

### Changed
- **The server redirect is now native**: a hook on the native wrapper of `HttpRequest.init` (`0x1ce350c`) rewrites
  CloudCell/CDN URLs to `http://127.0.0.1:8780/_retr0host/<host><path>` ([retr0_redirect.c](patches/store_grant_patch/retr0_redirect.c),
  linked into the code cave by [cave.ld](patches/store_grant_patch/cave.ld)). The client now changes only
  `libRealRacing3.so`; Java and APKTool are no longer needed to build it. Needs RETR0 Server 0.2.0 or later
  (`/_retr0host/` paths).
- `build_patch.py` compiles C as well as assembly, refuses any allocated section other than `.text`, and writes
  `patch_data.json` (built cave bytes and hook words).

### Added
- **Button text** ([patches/ui_text/retr0_gui_patch.py](patches/ui_text/retr0_gui_patch.py)): a game-data patch
  that renames Settings › ENTER RACING CODE to "Change Username (Restart Required)" and its prompt to "Enter your
  new username (restart required):", built from the player's own files (`client.ps1 ui-text` on the server).
- Docs: the emulator-reboot caveat for in-place installs.

### Deprecated
- The Java redirect (`patches/local_server_redirect/`) is kept for reference only.

## [0.1.0] - 2026-11-20

First public release. Targets Real Racing 3 **14.0.1**, `arm64-v8a`.

### Added
- **Built-in server redirect** (`Redirect.smali`): CloudCell and asset-CDN requests go to `http://127.0.0.1:8780`
  with `X-RETR0-Host`; no Frida needed.
- **Store preservation grants**: hooks on `NimbleMTX::PurchaseStoreProduct` (`0xb8d6e4`) and `PackManager`'s pack
  purchase (`0x13ef7e8`) award allow-listed currency packages and packs through the game's non-purchase path.
- **Player name**: hooks on the player-name function (`0x135e944`) and the racing-code submit (`0x1516b1c`); the name
  lives in `files/doc/retr0_username.txt`.
- **Build scripts** with `--apk`, `--out`, `--ndk-bin`, `--build-tools`, `--keystore`, `--apktool`; reproducible,
  byte-identical builds; zip-aligned and debug-signed outputs.
- Documentation: how the client is patched, building, installing, one page per feature.

[0.2.0]: https://github.com/Tankonline/RETR0-Client/releases/tag/v0.2.0
[0.1.0]: https://github.com/Tankonline/RETR0-Client/releases/tag/v0.1.0
