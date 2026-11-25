# RETR0 link: connect over Wi-Fi to a RETR0 server

The **RETR0 link** lets the game reach a RETR0 server running on another computer on the same home network, for
any CPU type (also 32-bit ARM devices, where the native redirect is not available). No USB cable, no
`adb reverse`, no setup on the device.

Source: [`patches/retr0_link/`](../../patches/retr0_link/). Needs a RETR0 Server with LAN mode (RETR0-Server
`docs/features/lan-mode.md`).

## How it works

1. **Redirect** (`src/com/retr0/Redirect.java`). `HttpRequest.init` in `classes2.dex` gets one added instruction
   as its first line: `url = com.retr0.Redirect.rewrite(url)`. CloudCell and asset-CDN URLs (`*.cloudcell.com`,
   `*.exos.fm`, `firemonkeys.akamaized.net`) become `http://127.0.0.1:8780/_retr0host/<host><path>`, the same form
   the native redirect uses. Every other URL is unchanged.
2. **Link** (`src/com/retr0/Link.java`), started by the first redirected request:
   - listens on `127.0.0.1:8780` inside the app. If that port is already taken (`adb reverse` on the emulator), it
     does nothing and the existing setup keeps working;
   - finds the server: the address in `files/retr0_server.txt` if present, else the RETR0 discovery broadcast
     (UDP 8799, `RETR0?` → `RETR0 <port>`; the server is the reply's sender), else the last server that answered
     (`files/retr0_last_server.txt`). It re-checks every 30 s, and at once after a failed connection;
   - relays each connection to the server byte for byte. The game still only talks to `127.0.0.1`, so the app's
     network security config needs no change.
   - No server found: connections are closed and the game behaves as offline. Logs: logcat tag `RETR0`.

`files/` is `/sdcard/Android/data/com.ea.games.r3_row/files/`. Only IP addresses are accepted there (no name lookups).

## Build

`patches/retr0_link/build_link.py` (Python 3, JDK, Android SDK build-tools and platform `android-35`, APKTool):

1. compiles the two classes (`javac --release 8`, `d8 --min-api 26`) into `classes6.dex`;
2. decodes the original APK's code with APKTool, adds the one call to `HttpRequest.init`, rebuilds, keeps
   `classes2.dex`;
3. takes the native-patched client from `patches/store_grant_patch/build_patch.py`, replaces `classes2.dex`, adds
   `classes6.dex`, keeps every other entry, zip-aligns and writes an in-place copy and a debug-signed copy.

Pass `--apk` (your original 14.0.1 APK) and `--base` (the client from `build_patch.py`); `--help` lists the tool
paths it needs. It checks the original APK's SHA-256 first (14.0.1 only). Outputs:
`rr3_14.0.1_retr0_lan_client.apk` (in-place swap, same as the emulator install) and `..._signed.apk`.

## Install

Rooted devices: the in-place swap in [installing.md](../installing.md) keeps the game's data. As on the emulator,
the swap does not survive a reboot (Android re-checks the signature): swap again after a reboot. `client.ps1`
still assumes the emulator's `su`; devices rooted through `adb root` (like the K1) are swapped by hand for now.

## Tested

Run 35: NVIDIA SHIELD Tablet K1 (LineageOS 15.1, Android 8.1, armeabi-v7a), server on a Windows PC over Wi-Fi.
The game found the server by broadcast, synced, opened Daily Rewards and uploaded a cloud save; after a restart it
found the server again.

## Limits

- 64-bit-only additions of the native patch (store grants, player name) are not in the 32-bit library yet.
- The link carries plain HTTP inside your home network; it is not meant for the internet.
