// Project RETR0 - "RETR0 link": connects the game to a RETR0 server on the local network. Independently written.
//
// Started by the first redirected request (Redirect.rewrite). It
//   1. listens on 127.0.0.1:8780 inside the app. If that port is already taken (adb reverse on the test emulator,
//      or a future built-in server), it does nothing and the existing setup keeps working;
//   2. finds the server: a manual address in files/retr0_server.txt ("192.168.0.39" or "192.168.0.39:8780"), else
//      the RETR0 discovery broadcast (UDP 8799: "RETR0?" -> "RETR0 <port>", server = the reply's sender), else the
//      last server that answered (files/retr0_last_server.txt);
//   3. relays every connection to that server, byte for byte. The game itself still only talks to 127.0.0.1, which
//      the app's network security config allows in plain HTTP; the relay is a raw socket, so no config change is
//      needed.
// No server found: connections are closed, and the game behaves as it does offline. Discovery is retried.
// Logs go to logcat with the tag RETR0.
package com.retr0;

import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;

public final class Link {
    static final String TAG = "RETR0";
    static final int LOCAL_PORT = 8780, DISCOVERY_PORT = 8799;
    static final String FILES = "/sdcard/Android/data/com.ea.games.r3_row/files/";
    static final Charset ASCII = Charset.forName("US-ASCII");

    private static boolean started;
    private static volatile InetSocketAddress server;
    private static final Object lock = new Object();

    private Link() { }

    public static void start() {
        synchronized (Link.class) {
            if (started) return;
            started = true;
        }
        Thread t = new Thread(new Runnable() { public void run() { listen(); } }, "RETR0-link");
        t.setDaemon(true);
        t.start();
    }

    private static void listen() {
        ServerSocket ss;
        try {
            ss = new ServerSocket();
            ss.setReuseAddress(true);
            ss.bind(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), LOCAL_PORT), 64);
        } catch (Exception e) {
            Log.i(TAG, "link idle: 127.0.0.1:" + LOCAL_PORT + " is already served (" + e.getMessage() + ")");
            return;
        }
        Log.i(TAG, "link listening on 127.0.0.1:" + LOCAL_PORT);
        Thread finder = new Thread(new Runnable() { public void run() { findLoop(); } }, "RETR0-find");
        finder.setDaemon(true);
        finder.start();
        while (true) {
            try {
                final Socket in = ss.accept();
                Thread t = new Thread(new Runnable() { public void run() { relay(in); } }, "RETR0-relay");
                t.setDaemon(true);
                t.start();
            } catch (Exception e) {
                Log.w(TAG, "accept failed: " + e);
                sleep(500);
            }
        }
    }

    // Keeps a server address while the game runs: re-checks every 30 s, or sooner when a connection failed.
    private static void findLoop() {
        while (true) {
            InetSocketAddress found = find();
            synchronized (lock) {
                if (found != null && !found.equals(server)) Log.i(TAG, "server: " + found);
                if (found != null) server = found;
                lock.notifyAll();
                try { lock.wait(server == null ? 5000 : 30000); } catch (InterruptedException e) { return; }
            }
        }
    }

    private static InetSocketAddress find() {
        InetSocketAddress manual = parse(read(FILES + "retr0_server.txt"));
        if (manual != null) return manual;
        InetSocketAddress d = discover();
        if (d != null) {
            write(FILES + "retr0_last_server.txt", d.getAddress().getHostAddress() + ":" + d.getPort());
            return d;
        }
        return parse(read(FILES + "retr0_last_server.txt"));
    }

    private static InetSocketAddress discover() {
        DatagramSocket s = null;
        try {
            s = new DatagramSocket();
            s.setBroadcast(true);
            s.setSoTimeout(700);
            byte[] q = "RETR0?".getBytes(ASCII);
            for (int attempt = 0; attempt < 3; attempt++) {
                for (InetAddress b : broadcasts()) s.send(new DatagramPacket(q, q.length, b, DISCOVERY_PORT));
                long until = System.currentTimeMillis() + 900;
                while (System.currentTimeMillis() < until) {
                    byte[] buf = new byte[64];
                    DatagramPacket p = new DatagramPacket(buf, buf.length);
                    try { s.receive(p); } catch (SocketTimeoutException e) { break; }
                    String r = new String(buf, 0, p.getLength(), ASCII).trim();
                    if (r.startsWith("RETR0 ")) {
                        int port = Integer.parseInt(r.substring(6).trim());
                        return new InetSocketAddress(p.getAddress(), port);
                    }
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "discovery failed: " + e);
        } finally {
            if (s != null) s.close();
        }
        return null;
    }

    private static List<InetAddress> broadcasts() {
        List<InetAddress> out = new ArrayList<InetAddress>();
        try {
            for (Enumeration<NetworkInterface> e = NetworkInterface.getNetworkInterfaces(); e.hasMoreElements(); ) {
                NetworkInterface ni = e.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                for (InterfaceAddress a : ni.getInterfaceAddresses())
                    if (a.getAddress() instanceof Inet4Address && a.getBroadcast() != null && !out.contains(a.getBroadcast()))
                        out.add(a.getBroadcast());
            }
        } catch (Exception ignored) { }
        try { out.add(InetAddress.getByName("255.255.255.255")); } catch (Exception ignored) { }
        return out;
    }

    private static void relay(Socket in) {
        Socket out = null;
        try {
            InetSocketAddress target = waitForServer(6000);
            if (target == null) { Log.w(TAG, "no RETR0 server found on the network"); return; }
            out = new Socket();
            out.connect(target, 4000);
            out.setTcpNoDelay(true);
            in.setTcpNoDelay(true);
            final Socket a = in, b = out;
            Thread up = new Thread(new Runnable() { public void run() { pump(a, b); } }, "RETR0-up");
            up.setDaemon(true);
            up.start();
            pump(b, a);
            up.join(30000);
        } catch (Exception e) {
            Log.w(TAG, "relay failed: " + e);
            synchronized (lock) { lock.notifyAll(); }      // look for the server again
        } finally {
            close(in);
            close(out);
        }
    }

    private static InetSocketAddress waitForServer(long ms) {
        long until = System.currentTimeMillis() + ms;
        synchronized (lock) {
            while (server == null) {
                long left = until - System.currentTimeMillis();
                if (left <= 0) return null;
                try { lock.wait(left); } catch (InterruptedException e) { return null; }
            }
            return server;
        }
    }

    private static void pump(Socket from, Socket to) {
        byte[] buf = new byte[64 * 1024];
        try {
            InputStream i = from.getInputStream();
            OutputStream o = to.getOutputStream();
            int n;
            while ((n = i.read(buf)) > 0) { o.write(buf, 0, n); o.flush(); }
        } catch (Exception ignored) {
        } finally {
            try { to.shutdownOutput(); } catch (Exception ignored) { }
        }
    }

    static InetSocketAddress parse(String s) {
        if (s == null) return null;
        s = s.trim();
        if (s.isEmpty()) return null;
        try {
            int port = 8780;
            int c = s.lastIndexOf(':');
            if (c > 0 && s.indexOf(':') == c) { port = Integer.parseInt(s.substring(c + 1).trim()); s = s.substring(0, c).trim(); }
            if (!s.matches("[0-9.]+")) return null;          // addresses only: no name lookups
            return new InetSocketAddress(InetAddress.getByName(s), port);
        } catch (Exception e) {
            return null;
        }
    }

    private static String read(String path) {
        File f = new File(path);
        if (!f.isFile() || f.length() > 256) return null;
        try {
            java.io.FileInputStream in = new java.io.FileInputStream(f);
            try {
                byte[] b = new byte[(int) f.length()];
                int n = in.read(b);
                return n > 0 ? new String(b, 0, n, ASCII) : null;
            } finally { in.close(); }
        } catch (Exception e) {
            return null;
        }
    }

    private static void write(String path, String text) {
        try {
            FileOutputStream o = new FileOutputStream(path);
            try { o.write(text.getBytes(ASCII)); } finally { o.close(); }
        } catch (Exception ignored) { }
    }

    private static void close(Socket s) { if (s != null) try { s.close(); } catch (Exception ignored) { } }

    private static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException ignored) { } }
}
