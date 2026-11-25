// Project RETR0 - Java redirect for Real Racing 3 14.0.1 (any CPU type). Independently written.
//
// HttpRequest.init (classes2.dex) calls Redirect.rewrite(url) as its first instruction. A CloudCell or asset-CDN URL
// (*.cloudcell.com, *.exos.fm, firemonkeys.akamaized.net) becomes
//     http://127.0.0.1:8780/_retr0host/<original host><original path and query>
// (the same form as the native redirect; the RETR0 server takes the host back out of the path). Every other URL is
// returned unchanged. 127.0.0.1:8780 is served either by `adb reverse` (emulator, development) or by Link, which
// relays it to a RETR0 server found on the local network.
package com.retr0;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class Redirect {
    private static final Pattern URL = Pattern.compile("^[hH][tT][tT][pP][sS]?://([^/:?#]+)(?::[0-9]+)?(.*)$");
    private static final Pattern HOSTS =
            Pattern.compile("(?i)(.*[.])?cloudcell[.]com|(.*[.])?exos[.]fm|firemonkeys[.]akamaized[.]net");
    static final String LOCAL = "http://127.0.0.1:8780/_retr0host/";

    private Redirect() { }

    public static String rewrite(String url) {
        if (url == null) return null;
        try {
            Matcher m = URL.matcher(url);
            if (!m.matches()) return url;
            String host = m.group(1);
            if (!HOSTS.matcher(host).matches()) return url;
            String rest = m.group(2);
            if (rest.isEmpty() || rest.charAt(0) == '?' || rest.charAt(0) == '#') rest = "/" + rest;
            Link.start();
            return LOCAL + host + rest;
        } catch (Throwable t) {
            return url;     // never break the game's own request path
        }
    }
}
