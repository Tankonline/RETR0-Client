"""Project RETR0 - build the LAN-capable RETR0 client (RETR0 link) for RR3 14.0.1. Never touches 00_ORIGINAL.

Steps
  1. javac (release 8, against android.jar) + d8 (min API 26): src/com/retr0/{Redirect,Link}.java -> classes6.dex
     (the original APK has classes.dex .. classes5.dex; Android loads classesN.dex in order).
  2. apktool decodes the original APK's code, inserts ONE call as the first instruction of
     com.firemonkeys.cloudcellapi.HttpRequest.init:  p3 (url) = com.retr0.Redirect.rewrite(p3)
     and rebuilds; its classes2.dex is kept (the Redirect class itself lives in classes6.dex).
  3. Takes the native-patched client APK from store_grant_patch/build_patch.py (64-bit hooks, unchanged 32-bit
     library), replaces classes2.dex, adds classes6.dex, keeps every other entry and its compression,
     zip-aligns (16 KB pages for stored .so) and writes a debug-signed copy.

Outputs (in --out): rr3_14.0.1_retr0_lan_client.apk (in-place swap), rr3_14.0.1_retr0_lan_client_signed.apk.
"""
import argparse, glob, hashlib, os, shutil, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SDK = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Android/Sdk"
ORIGINAL_SHAS = {   # the same 14.0.1 APK; only the signing block bytes differ (same EA certificate)
    "dcfe3788004444bd69e2fb839c18a973b488e94f46f1b818b6c005afdcad1d5f",
    "eb38c10386ddbba2cb121ed3867822623f6b82df86e962e003667d4fac404e3d",
}
SIG = ".method public init(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;[BIJZDZZI)V\n    .locals 12\n"
REWRITE = ("\n    # RETR0: send CloudCell/CDN requests to the RETR0 server (com.retr0.Redirect, classes6.dex)\n"
           "    invoke-static {p3}, Lcom/retr0/Redirect;->rewrite(Ljava/lang/String;)Ljava/lang/String;\n\n"
           "    move-result-object p3\n")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd):
    print(">", " ".join(str(c) for c in cmd)[:200], flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def build_link_dex(work: Path, android_jar: Path, build_tools: Path) -> Path:
    cls = work / "classes"
    if cls.exists():
        shutil.rmtree(cls)
    cls.mkdir(parents=True)
    srcs = sorted(glob.glob(str(HERE / "src/com/retr0/*.java")))
    run(["javac", "--release", "8", "-Xlint:-options", "-encoding", "UTF-8", "-cp", android_jar, "-d", cls] + srcs)
    dexdir = work / "dex"
    if dexdir.exists():
        shutil.rmtree(dexdir)
    dexdir.mkdir()
    classes = sorted(glob.glob(str(cls / "com/retr0/*.class")))
    run([build_tools / "d8.bat", "--release", "--min-api", "26", "--lib", android_jar, "--output", dexdir] + classes)
    return dexdir / "classes.dex"


def build_hook_dex(work: Path, apk: Path, apktool: Path) -> Path:
    dec = work / "dec"
    if dec.exists():
        shutil.rmtree(dec)
    run(["java", "-jar", apktool, "d", "-r", "-f", "-o", dec, apk])
    hr = dec / "smali_classes2/com/firemonkeys/cloudcellapi/HttpRequest.smali"
    s = hr.read_text(encoding="utf-8")
    assert s.count(SIG) == 1, "HttpRequest.init signature not found"
    hr.write_text(s.replace(SIG, SIG + REWRITE, 1), encoding="utf-8", newline="\n")
    built = work / "rebuilt.apk"
    run(["java", "-jar", apktool, "b", "-f", "-o", built, dec])
    out = work / "classes2_hook.dex"
    out.write_bytes(zipfile.ZipFile(built).read("classes2.dex"))
    return out


def assemble(base: Path, hook: Path, link: Path, out_unaligned: Path) -> None:
    with zipfile.ZipFile(base) as zin, zipfile.ZipFile(out_unaligned, "w") as zout:
        names = zin.namelist()
        assert "classes6.dex" not in names, "base APK already has classes6.dex"
        for info in zin.infolist():
            data = hook.read_bytes() if info.filename == "classes2.dex" else zin.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type, zi.external_attr = info.compress_type, info.external_attr
            zout.writestr(zi, data)
        zi = zipfile.ZipInfo("classes6.dex", date_time=(2008, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zout.writestr(zi, link.read_bytes())


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the LAN-capable RETR0 client (RETR0 link).")
    ap.add_argument("--apk", type=Path, default=ROOT / "00_ORIGINAL/APK/real-racing-3-14-0-1.apk",
                    help="your original RR3 14.0.1 APK (SHA-256 checked)")
    ap.add_argument("--base", type=Path, default=ROOT / "08_TESTING/runtime/out/apk/rr3_14.0.1_retr0_client.apk",
                    help="native-patched client APK from store_grant_patch/build_patch.py")
    ap.add_argument("--out", type=Path, default=ROOT / "08_TESTING/runtime/out/apk")
    ap.add_argument("--apktool", type=Path, default=Path(r"C:\tools\APKTool\apktool_3.0.3.jar"))
    ap.add_argument("--build-tools", type=Path, default=SDK / "build-tools/36.0.0")
    ap.add_argument("--android-jar", type=Path, default=SDK / "platforms/android-35/android.jar")
    ap.add_argument("--keystore", type=Path, default=Path.home() / ".android/debug.keystore")
    a = ap.parse_args()
    assert sha(a.apk) in ORIGINAL_SHAS, f"not the RR3 14.0.1 APK: {a.apk}"
    work = a.out / "link_work"
    work.mkdir(parents=True, exist_ok=True)
    link = build_link_dex(work, a.android_jar, a.build_tools)
    hook = build_hook_dex(work, a.apk, a.apktool)
    unaligned = work / "unaligned.apk"
    assemble(a.base, hook, link, unaligned)
    client = a.out / "rr3_14.0.1_retr0_lan_client.apk"
    signed = a.out / "rr3_14.0.1_retr0_lan_client_signed.apk"
    run([a.build_tools / "zipalign.exe", "-P", "16", "-f", "4", unaligned, client])
    shutil.copyfile(client, signed)
    run([a.build_tools / "apksigner.bat", "sign", "--ks", a.keystore, "--ks-pass", "pass:android",
         "--key-pass", "pass:android", "--ks-key-alias", "androiddebugkey", signed])
    run([a.build_tools / "apksigner.bat", "verify", signed])
    for p in (link, hook, client, signed):
        print(f"{p.name:44} {p.stat().st_size:>11,} bytes  sha256 {sha(p)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
