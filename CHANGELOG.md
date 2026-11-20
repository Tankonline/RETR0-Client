# Changelog

All notable changes to the RETR0 Client patches. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/Tankonline/RETR0-Client/releases/tag/v0.1.0
