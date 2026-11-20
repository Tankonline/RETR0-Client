# Installing and playing

The install and play commands live in the [RETR0 Server](https://github.com/Tankonline/RETR0-Server) repository
(`server\client.ps1`, `server\play.cmd`), because playing needs the server anyway. Full walkthrough, including the
emulator and asset packs: [RETR0-Server setup guide](https://github.com/Tankonline/RETR0-Server/blob/main/docs/08-setup-guide.md).

> **Back up first:** copy the device's `Android/data/com.ea.games.r3_row/` folder before changing anything.

## 1. Give the server your APKs

Copy into the server's `server\client\apk\`:

- `rr3_14.0.1_retr0_client.apk` and `rr3_14.0.1_retr0_client_signed.apk` (from your build);
- your original APK, renamed `rr3_14.0.1_original.apk` (for `restore`).

## 2. Put the client on the emulator

| Command | Effect |
|---|---|
| `server\client.ps1 apply` | Swaps the installed `base.apk` for the RETR0 client **in place** (root), keeping owner, mode, SELinux label and timestamp, then `cmd package compile -f -m verify`. **Game data is kept** |
| `server\client.ps1 install-fresh` | Uninstalls (asks first, deletes data) and installs the debug-signed client |
| `server\client.ps1 status` | Which APK is installed (by SHA-256) |
| `server\client.ps1 restore` | Puts the original APK back in place, data kept |

The in-place swap works because the game loads its native libraries straight from `base.apk`
(`extractNativeLibs=false`) and Android does not re-check an installed APK's signature at app start. An emulator with
a Google APIs image (root via `su`) is required for `apply`/`restore`.

> [!WARNING]
> **After an emulator restart** the swapped APK is gone: Android re-checks signatures at boot and removes the app's
> code (your data stays). Reinstall the original over it, `adb install -r <original APK>`, then `client.ps1 apply`.

## 3. Play

```powershell
server\retr0_server.cmd start -WithSync
server\play.cmd
```

`play.cmd` checks the emulator runs the RETR0 client, sets `adb reverse tcp:8780 tcp:8780` and starts the game.

## Using the features

- **Store:** press BUY on a currency package or currency pack.
- **Player name:** Settings → Enter Racing Code → type the name → "code accepted" → restart the game. The name is in
  `files/doc/retr0_username.txt` on the device; delete it to go back to "Guest".
- **Button text (optional):** `server\client.ps1 ui-text` renames that button to "Change Username (Restart
  Required)" by editing two of the game's UI files on the device; `server\client.ps1 ui-text-restore` undoes it.
  See [features/username.md](features/username.md#button-text).
- **Logs:** each feature writes a `RETR0 …` line to logcat (`adb logcat | findstr RETR0`).
