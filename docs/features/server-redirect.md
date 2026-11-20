# Feature · Built-in server redirect

**What it does:** makes the game send all its CloudCell and asset-CDN traffic to the RETR0 server on your PC, with
no Frida and no time limit. Every other host is left alone.

## Background

The game hard-codes its servers (`0037-connect.cloudcell.com`, `firemonkeys.akamaized.net`, …) and always uses HTTPS
on port 443 (NW-85, NW-86). Two facts made a local server possible:

- All CloudCell HTTP, including asset downloads, goes through **one Java class**,
  `com.firemonkeys.cloudcellapi.HttpRequest`, via `init(userAgent, method, url, body, …)` (NW-01). On the native
  side, one function builds those Java calls for every request.
- The app's `network_security_config` allows plain HTTP **only to `127.0.0.1`**.

During research a **Frida** hook on `HttpRequest.init` rewrote those URLs to `http://127.0.0.1:8780` and added a
header `X-RETR0-Host: <original host>` ([research-tools/retr0_redirect_java.js](https://github.com/Tankonline/RETR0-Server/blob/main/research-tools/retr0_redirect_java.js)).
That worked, but only while a Frida session was attached. When a timed session ended, the game silently lost the
server, and online screens locked (see [special-events.md](special-events.md)).

## How it is built (since 0.2.0: native)

The redirect is a hook in the native patch, like the other features
([how the client is patched](../how-the-client-is-patched.md)). The hooked function, ELF `0x1ce350c`, is the native
wrapper that turns a CloudCell request object into the Java `HttpRequest.init` call; the request's full URL is a
libc++ `std::string` at `request + 0x10`.

```
0x1ce350c(this, JNIEnv*, request, …):
    b redir_entry                                  ← replaces the first instruction (sub sp, sp, #0xe0)
redir_entry:  save x0–x8 · retr0_rewrite_request(request) · restore · sub sp, sp, #0xe0 · b 0x1ce3510
```

[`retr0_redirect.c`](../../patches/store_grant_patch/retr0_redirect.c) (freestanding C, no libc) reads the URL
(short or long `std::string` form), and if the host is `*.cloudcell.com`, `*.exos.fm` or `firemonkeys.akamaized.net`
(any case, port dropped) rewrites it with the game's own `std::string::assign` to

```
http://127.0.0.1:8780/_retr0host/<original host><original path and query>
```

A native hook cannot add a header the way the Java version did, so the original host travels in the path; the
server takes it back out (`/_retr0host/<host>/…`). Every other URL is unchanged. The first four rewrites are logged
as `RETR0 redirect: …`.

The C file is compiled with `-Os -fno-pic -fno-pie -ffreestanding -fno-builtin -mgeneral-regs-only` and linked
together with the assembly by [`cave.ld`](../../patches/store_grant_patch/cave.ld), which puts code and constant
strings in the cave. The build refuses any other allocated section: an early build reached its log counter through a
GOT slot outside the cave, which would have crashed the game on the first request.

On the emulator, `adb reverse tcp:8780 tcp:8780` connects the device's `127.0.0.1:8780` to the PC; `play.cmd` sets it
every time.

## The 0.1.0 version (Java)

0.1.0 did the same in the Java layer: [`Redirect.smali`](../../patches/local_server_redirect/Redirect.smali) inserted
into `HttpRequest.init` by [`build_redirect_dex.py`](../../patches/local_server_redirect/build_redirect_dex.py)
(APKTool), shipped as a replacement `classes2.dex`. It is kept for reference; it needed Java and APKTool to build and
changed two files in the APK instead of one.

## Verified

- **Run 30 (native, 0.2.0):** logcat shows `RETR0 redirect: http://127.0.0.1:8780/_retr0host/0037-connect.cloudcell.com/…`,
  syncs succeed, and the owner confirmed Special Events, Store BUY, the player name and Settings › Download All Assets
  (the CDN path).
- **Run 25 (Java, 0.1.0):** with no Frida attached, `/time` and `CC_Sync.php` succeed with `X-RETR0-Host`.
