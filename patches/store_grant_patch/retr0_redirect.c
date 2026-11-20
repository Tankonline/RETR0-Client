/* Project RETR0 - native local-server redirect for Real Racing 3 14.0.1 (arm64-v8a), independently written.
 *
 * Called from redir_entry (store_grant_patch.S), which hooks the entry of the native wrapper that hands every
 * CloudCell HTTP request to Java (ELF 0x1ce350c: builds the Java strings from the request object and calls
 * com.firemonkeys.cloudcellapi.HttpRequest.init). The request object keeps the full URL as a libc++ std::string
 * at +0x10. For a CloudCell or CDN host (*.cloudcell.com, *.exos.fm, firemonkeys.akamaized.net) the URL is
 * rewritten to
 *     http://127.0.0.1:8780/_retr0host/<original host><original path and query>
 * The RETR0 server takes the host back out of the path. Every other URL is left unchanged.
 *
 * Built freestanding (no libc): -ffreestanding -fno-builtin -mgeneral-regs-only, linked into the code cave.
 */
typedef unsigned long size_t;

extern void str_assign(void *s, const char *cstr);       /* libc++ std::string::assign(const char*), 0x15da06c */
extern void game_log(const char *fmt, ...);               /* the game's printf-style logger, 0x109fa18 */
extern unsigned char redir_log_count;                     /* one spare byte of writable memory (0x1f9c19f) */

static const char LOCAL[] = "http://127.0.0.1:8780/_retr0host/";

static int prefix(const char *s, size_t n, const char *p) {
    size_t i = 0;
    for (; p[i]; i++)
        if (i >= n || s[i] != p[i]) return 0;
    return 1;
}

static int suffix(const char *h, size_t n, const char *suf) {
    size_t m = 0;
    while (suf[m]) m++;
    if (m > n) return 0;
    for (size_t i = 0; i < m; i++) {
        char c = h[n - m + i];
        if (c >= 'A' && c <= 'Z') c += 32;
        if (c != suf[i]) return 0;
    }
    return 1;
}

static int redirect_host(const char *h, size_t n) {
    return (n == 25 && suffix(h, n, "firemonkeys.akamaized.net"))
        || suffix(h, n, ".cloudcell.com")
        || suffix(h, n, ".exos.fm");
}

void retr0_rewrite_request(unsigned char *req) {
    unsigned char *s = req + 0x10;
    const char *url;
    size_t len;
    if (s[0] & 1) {                                   /* long form: size at +8, data pointer at +16 */
        len = *(size_t *)(s + 8);
        url = *(const char **)(s + 16);
    } else {                                          /* short form: size = byte0 >> 1, data at +1 */
        len = s[0] >> 1;
        url = (const char *)(s + 1);
    }
    if (!url) return;

    size_t i;
    if (prefix(url, len, "https://")) i = 8;
    else if (prefix(url, len, "http://")) i = 7;
    else return;

    size_t hs = i;
    while (i < len && url[i] != ':' && url[i] != '/' && url[i] != '?') i++;
    size_t hn = i - hs;
    if (hn == 0 || hn > 253 || !redirect_host(url + hs, hn)) return;
    if (i < len && url[i] == ':')                     /* drop the port */
        while (i < len && url[i] != '/' && url[i] != '?') i++;

    char buf[2048];
    size_t o = 0;
    for (size_t k = 0; LOCAL[k]; k++) buf[o++] = LOCAL[k];
    for (size_t k = 0; k < hn; k++) buf[o++] = url[hs + k];
    if (i >= len || url[i] == '?') buf[o++] = '/';
    if (o + (len - i) + 1 > sizeof buf) return;       /* too long: leave the request alone */
    for (; i < len; i++) buf[o++] = url[i];
    buf[o] = 0;

    if (redir_log_count < 4) {                        /* log the first few, not every CDN range request */
        redir_log_count++;
        game_log("RETR0 redirect: %s\n", buf);
    }
    str_assign(s, buf);
}
