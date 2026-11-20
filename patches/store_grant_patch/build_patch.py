"""Build the RETR0 client from the original Real Racing 3 14.0.1 APK (arm64 libRealRacing3.so patch only).

Never touches the original APK: reads it and writes new files to the output folder.

Steps
  1. Assemble store_grant_patch.S and compile retr0_redirect.c with the NDK clang, link both with cave.ld into the
     unused zero padding before .text (va 0x9876c8, 0x938 bytes).
  2. Check the cave is empty and that every hooked instruction is exactly the vanilla one, then write the code and
     one `b <handler>` per hook (5 hooks: store packages, store packs, player name, racing code, server redirect).
  3. Fix the library's zip CRC (local + central header). The library is stored, so its size and offset are unchanged.
  4. zip-align (16 KB pages for the stored .so) and write a debug-signed copy.
  5. Write patch_data.json: the pre-built cave bytes and each hook's expected/new bytes, for a planned standalone
     patcher that will need no NDK, Java or SDK tools.

Outputs: rr3_14.0.1_retr0_client.apk (in-place swap), rr3_14.0.1_retr0_client_signed.apk (new install),
patch_data.json.
"""
import hashlib, json, os, re, struct, subprocess, sys, tempfile, zlib, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC_APK = ROOT / "00_ORIGINAL/APK/real-racing-3-14-0-1.apk"
OUT_DIR = ROOT / "08_TESTING/runtime/out/apk"
OUT_APK = OUT_DIR / "rr3_14.0.1_retr0_unaligned.apk"
CLIENT_APK = OUT_DIR / "rr3_14.0.1_retr0_client.apk"
CLIENT_SIGNED = OUT_DIR / "rr3_14.0.1_retr0_client_signed.apk"
PATCH_DATA = OUT_DIR / "patch_data.json"
SDK = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Android/Sdk"
BUILD_TOOLS = SDK / "build-tools/36.0.0"
NDK = SDK / "ndk/28.2.13676358/toolchains/llvm/prebuilt/windows-x86_64/bin"
DEBUG_KEYSTORE = Path.home() / ".android/debug.keystore"
LIB = "lib/arm64-v8a/libRealRacing3.so"
EXPECT_SHA = "dcfe3788004444bd69e2fb839c18a973b488e94f46f1b818b6c005afdcad1d5f"

CAVE, CAVE_LEN = 0x9876C8, 0x938          # zero padding between .eh_frame and .text (RX segment)
SYMS = {
    # store preservation grants (SP-14)
    "orig_continue": 0xB8D6E8, "pack_continue": 0x13EF7EC, "store_lookup": 0xB84354, "reward_parse": 0xCEE2E0,
    "mtx_can_award": 0xB873C0, "mtx_award": 0xB879FC, "reward_dtor": 0xA36FEC,
    "save_request": 0x13A14B8, "game_log": 0x109FA18,
    "got_store_mgr": 0x1F6DDF0, "got_save_mgr": 0x1F6D818,
    # username (SV-27): player-name function, racing-code submit, libc PLT stubs, spare state bytes
    "name_continue": 0x135E948, "promo_continue": 0x1516B20, "str_assign": 0x15DA06C,
    "fopen": 0x1E17CE0, "fclose": 0x1E17CF0, "fgets": 0x1E18AD0, "fputs": 0x1E18AE0, "malloc": 0x1E18BA0,
    "name_slot": 0x1F9C1A0,
    # native server redirect: request-to-Java wrapper, 1 spare byte for the log counter
    "redir_continue": 0x1CE3510, "redir_log_count": 0x1F9C19F,
}
# (address, vanilla first instruction, handler symbol, what it is)
HOOKS = [
    (0xB8D6E4, "ff4302d1", "grant_entry", "NimbleMTX::PurchaseStoreProduct: sub sp, sp, #0x90"),
    (0x13EF7E8, "e80f19fc", "pack_entry", "PackManager pack purchase: str d8, [sp, #-0x70]!"),
    (0x135E944, "ff0307d1", "name_entry", "player-name function: sub sp, sp, #0x1c0"),
    (0x1516B1C, "ffc305d1", "promo_entry", "racing-code submit: sub sp, sp, #0x170"),
    (0x1CE350C, "ff8303d1", "redir_entry", "CloudCell request -> Java HttpRequest wrapper: sub sp, sp, #0xe0"),
]
CFLAGS = ["--target=aarch64-linux-android", "-Os", "-fno-pic", "-fno-pie", "-fno-unroll-loops", "-fno-vectorize",
          "-fno-slp-vectorize", "-ffreestanding", "-fno-builtin", "-mgeneral-regs-only",
          "-fno-stack-protector", "-fno-jump-tables", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables"]


def tool(name: str) -> str:
    exe = NDK / (name + ".exe")
    return str(exe if exe.exists() else NDK / name)


def build_handler(tmp: Path):
    s_obj, c_obj, elf = tmp / "p.o", tmp / "r.o", tmp / "p.elf"
    subprocess.run([tool("clang"), "--target=aarch64-linux-android", "-c", str(HERE / "store_grant_patch.S"),
                    "-o", str(s_obj)], check=True)
    subprocess.run([tool("clang"), *CFLAGS, "-c", str(HERE / "retr0_redirect.c"), "-o", str(c_obj)], check=True)
    ld = [tool("ld.lld"), "-static", "--no-rosegment", "-T", str(HERE / "cave.ld"), "-o", str(elf), str(s_obj), str(c_obj)]
    ld += [f"--defsym={k}=0x{v:x}" for k, v in SYMS.items()]
    subprocess.run(ld, check=True)
    # Only .text is copied into the cave, so any other allocated section (.got, .data, ...) would be missing at run
    # time: refuse it.
    secs = subprocess.run([tool("llvm-readelf"), "-S", "-W", str(elf)], check=True, capture_output=True, text=True).stdout
    row = re.compile(r"^\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+[0-9a-f]+\s+[0-9a-f]+\s+[0-9a-f]+\s+[0-9a-f]+\s+([A-Za-z]*)\s")
    rows = [m.groups() for m in map(row.match, secs.splitlines()) if m]
    assert any(n == ".text" for n, _ in rows), secs
    extra = [n for n, flags in rows if "A" in flags and n != ".text"]
    assert not extra, f"unexpected allocated sections in the patch: {extra}"
    subprocess.run([tool("llvm-objcopy"), "-O", "binary", "--only-section=.text", str(elf), str(tmp / "p.bin")], check=True)
    nm = subprocess.run([tool("llvm-nm"), str(elf)], check=True, capture_output=True, text=True).stdout
    syms = {p[2]: int(p[0], 16) for p in (l.split() for l in nm.splitlines()) if len(p) == 3}
    kinds = {p[1] for p in (l.split() for l in nm.splitlines()) if len(p) == 3}
    assert not kinds & set("dDbB"), f"patch code must not have writable data: {kinds}"
    return (tmp / "p.bin").read_bytes(), syms


def branch(src: int, dst: int) -> bytes:
    off = (dst - src) // 4
    assert -(1 << 25) <= off < (1 << 25)
    return struct.pack("<I", 0x14000000 | (off & 0x3FFFFFF))


def main() -> int:
    data = bytearray(SRC_APK.read_bytes())
    assert hashlib.sha256(data).hexdigest() == EXPECT_SHA, "original APK hash mismatch"
    z = zipfile.ZipFile(SRC_APK)
    info = z.getinfo(LIB)
    assert info.compress_type == zipfile.ZIP_STORED
    lh = info.header_offset
    name_len, extra_len = struct.unpack_from("<HH", data, lh + 26)
    lib_off = lh + 30 + name_len + extra_len
    lib = data[lib_off:lib_off + info.file_size]
    assert zlib.crc32(lib) & 0xFFFFFFFF == info.CRC
    lib_sha_vanilla = hashlib.sha256(lib).hexdigest()

    with tempfile.TemporaryDirectory() as t:
        code, syms = build_handler(Path(t))
    assert len(code) <= CAVE_LEN, f"patch code {len(code)} bytes > cave {CAVE_LEN}"
    assert syms["grant_entry"] == CAVE
    assert lib[CAVE:CAVE + CAVE_LEN] == bytes(CAVE_LEN), "cave not empty"
    hooks_out = []
    for addr, expect, handler, what in HOOKS:
        assert lib[addr:addr + 4] == bytes.fromhex(expect), f"unexpected instruction at 0x{addr:x} ({what})"
        new = branch(addr, syms[handler])
        hooks_out.append({"address": addr, "expect": expect, "new": new.hex(), "handler": handler, "what": what})
    lib[CAVE:CAVE + len(code)] = code
    for h in hooks_out:
        lib[h["address"]:h["address"] + 4] = bytes.fromhex(h["new"])
        print(f"hook 0x{h['address']:x} -> {h['handler']} 0x{syms[h['handler']]:x}")

    data[lib_off:lib_off + len(lib)] = lib
    crc = zlib.crc32(lib) & 0xFFFFFFFF
    struct.pack_into("<I", data, lh + 14, crc)                       # local header CRC
    eocd = data.rfind(b"PK\x05\x06")
    cd_off = struct.unpack_from("<I", data, eocd + 16)[0]
    p, fixed = cd_off, False
    while data[p:p + 4] == b"PK\x01\x02":
        n, e, c = struct.unpack_from("<HHH", data, p + 28)
        if data[p + 46:p + 46 + n].decode() == LIB:
            struct.pack_into("<I", data, p + 16, crc); fixed = True
        p += 46 + n + e + c
    assert fixed
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_APK.write_bytes(data)
    zipfile.ZipFile(OUT_APK).testzip()
    lib_sha = hashlib.sha256(lib).hexdigest()
    print(f"patch code {len(code)} of {CAVE_LEN} bytes at 0x{CAVE:x}; lib sha256 {lib_sha}")

    PATCH_DATA.write_text(json.dumps({
        "format": 1,
        "game": "Real Racing 3 14.0.1 (com.ea.games.r3_row, versionCode 14001)",
        "apk_sha256": EXPECT_SHA, "library": LIB,
        "library_sha256_vanilla": lib_sha_vanilla, "library_sha256_patched": lib_sha,
        "cave": {"address": CAVE, "length": CAVE_LEN, "code": code.hex()},
        "hooks": hooks_out,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"patch data {PATCH_DATA}")
    build_client()
    return 0


def build_client() -> None:
    """zip-align the patched APK (16 KB pages for stored .so files) and write a debug-signed copy."""
    subprocess.run([str(BUILD_TOOLS / "zipalign.exe"), "-P", "16", "-f", "4", str(OUT_APK), str(CLIENT_APK)], check=True)
    OUT_APK.unlink()
    subprocess.run([str(BUILD_TOOLS / "zipalign.exe"), "-c", "-P", "16", "4", str(CLIENT_APK)], check=True)
    subprocess.run(["cmd", "/c", str(BUILD_TOOLS / "apksigner.bat"), "sign", "--ks", str(DEBUG_KEYSTORE),
                    "--ks-key-alias", "androiddebugkey", "--ks-pass", "pass:android", "--key-pass", "pass:android",
                    "--out", str(CLIENT_SIGNED), str(CLIENT_APK)], check=True)
    subprocess.run(["cmd", "/c", str(BUILD_TOOLS / "apksigner.bat"), "verify", str(CLIENT_SIGNED)], check=True)
    for p in (CLIENT_APK, CLIENT_SIGNED):
        print(f"client {p} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


def configure(argv: list[str]) -> None:
    """Optional overrides for use outside the project layout (defaults: the project's paths)."""
    import argparse
    global SRC_APK, OUT_DIR, OUT_APK, CLIENT_APK, CLIENT_SIGNED, PATCH_DATA, NDK, BUILD_TOOLS, DEBUG_KEYSTORE
    ap = argparse.ArgumentParser(description="Build the RETR0 client APK and patch_data.json from an original RR3 14.0.1 APK.")
    ap.add_argument("--apk", type=Path, help="your original real-racing-3-14-0-1.apk (SHA-256 checked)")
    ap.add_argument("--out", type=Path, help="output folder")
    ap.add_argument("--ndk-bin", type=Path, help="NDK llvm bin folder (clang, ld.lld, llvm-objcopy, llvm-nm)")
    ap.add_argument("--build-tools", type=Path, help="Android build-tools folder (zipalign, apksigner)")
    ap.add_argument("--keystore", type=Path, help="debug keystore (alias androiddebugkey, password android)")
    a = ap.parse_args(argv)
    SRC_APK = a.apk or SRC_APK
    if a.out:
        OUT_DIR = a.out
    OUT_APK, CLIENT_APK, CLIENT_SIGNED, PATCH_DATA = (OUT_DIR / p.name for p in (OUT_APK, CLIENT_APK, CLIENT_SIGNED, PATCH_DATA))
    NDK = a.ndk_bin or NDK
    BUILD_TOOLS = a.build_tools or BUILD_TOOLS
    DEBUG_KEYSTORE = a.keystore or DEBUG_KEYSTORE


if __name__ == "__main__":
    configure(sys.argv[1:])
    sys.exit(main())
