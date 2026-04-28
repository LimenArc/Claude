package com.multimodelchat;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.EOFException;
import java.io.File;
import java.io.FileFilter;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.zip.GZIPInputStream;

public class MainActivity extends Activity {

    private static final String RELEASE_URL =
        "https://github.com/ggml-org/llama.cpp/releases/download/b8953/llama-b8953-bin-android-arm64.tar.gz";
    private static final int SERVER_PORT = 8080;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private WebView webView;
    private Process serverProcess;
    private String currentModelName = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if (serverBinary().exists()) {
            pickModel(false);
        } else {
            showSetup();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        killServer();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    private File binDir() { return new File(getFilesDir(), "llama"); }
    private File serverBinary() { return new File(binDir(), "llama-server"); }
    private File modelsDir() {
        File d = getExternalFilesDir("Models");
        if (d != null) d.mkdirs();
        return d;
    }

    // ── Setup ─────────────────────────────────────────────────────────────────

    private void showSetup() {
        LinearLayout root = darkLayout();
        root.setGravity(Gravity.CENTER);
        root.setPadding(64, 64, 64, 64);

        TextView title = label("First-Time Setup", 0xFFE2E8F0, 20);
        title.setGravity(Gravity.CENTER);
        root.addView(title);

        TextView desc = label(
            "Downloads the AI runtime once (~60 MB).\nAfter that the app works fully offline.",
            0xFF94A3B8, 13);
        desc.setGravity(Gravity.CENTER);
        desc.setPadding(0, 20, 0, 32);
        root.addView(desc);

        final ProgressBar bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setMax(100);
        bar.setVisibility(View.INVISIBLE);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        root.addView(bar, lp);

        final TextView status = label("", 0xFF94A3B8, 12);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, 8, 0, 20);
        status.setVisibility(View.INVISIBLE);
        root.addView(status);

        final Button btn = accentButton("Download Runtime");
        btn.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                btn.setEnabled(false);
                btn.setAlpha(0.5f);
                bar.setVisibility(View.VISIBLE);
                status.setVisibility(View.VISIBLE);
                runDownload(bar, status, btn);
            }
        });
        root.addView(btn);
        setContentView(root);
    }

    private void runDownload(final ProgressBar bar, final TextView status, final Button btn) {
        new Thread(new Runnable() {
            public void run() {
                try {
                    ui.post(new Runnable() { public void run() { status.setText("Connecting…"); } });
                    HttpURLConnection conn = openConn(new URL(RELEASE_URL));
                    final long total = conn.getContentLength();
                    File tmp = new File(getCacheDir(), "llama.tar.gz");
                    InputStream in = new BufferedInputStream(conn.getInputStream(), 65536);
                    FileOutputStream out = new FileOutputStream(tmp);
                    try {
                        byte[] buf = new byte[65536];
                        long done = 0; int n;
                        while ((n = in.read(buf)) != -1) {
                            out.write(buf, 0, n);
                            done += n;
                            final long d = done;
                            final int pct = total > 0 ? (int)(d * 60 / total) : 0;
                            ui.post(new Runnable() { public void run() {
                                bar.setProgress(pct);
                                status.setText("Downloading… " + d/1048576 + "/" + total/1048576 + " MB");
                            }});
                        }
                    } finally { in.close(); out.close(); }
                    conn.disconnect();

                    ui.post(new Runnable() { public void run() {
                        bar.setProgress(60); status.setText("Extracting…");
                    }});

                    File bd = binDir();
                    bd.mkdirs();
                    extractBinaries(tmp, bd, new Progress() {
                        public void onProgress(final int pct) {
                            ui.post(new Runnable() { public void run() {
                                bar.setProgress(60 + pct * 40 / 100);
                                status.setText("Extracting… " + pct + "%");
                            }});
                        }
                    });
                    serverBinary().setExecutable(true, false);
                    tmp.delete();
                    ui.post(new Runnable() { public void run() { pickModel(false); }});

                } catch (final Exception e) {
                    ui.post(new Runnable() { public void run() {
                        status.setText("Error: " + e.getMessage());
                        btn.setEnabled(true);
                        btn.setAlpha(1f);
                        btn.setText("Retry");
                        bar.setProgress(0);
                    }});
                }
            }
        }).start();
    }

    // ── Model Picker ──────────────────────────────────────────────────────────

    private void pickModel(final boolean fromChat) {
        File dir = modelsDir();
        final List<File> models = new ArrayList<File>();
        if (dir != null && dir.isDirectory()) {
            File[] files = dir.listFiles(new FileFilter() {
                public boolean accept(File f) { return f.getName().toLowerCase().endsWith(".gguf"); }
            });
            if (files != null) { Arrays.sort(files); models.addAll(Arrays.asList(files)); }
        }

        if (models.isEmpty()) {
            String path = dir != null ? dir.getAbsolutePath() : "(no external storage)";
            AlertDialog.Builder b = new AlertDialog.Builder(this)
                .setTitle("No Models Found")
                .setMessage("Copy .gguf model files to:\n\n" + path)
                .setPositiveButton("Refresh", new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface d, int w) { pickModel(fromChat); }
                })
                .setCancelable(false);
            if (fromChat) b.setNegativeButton("Cancel", null);
            b.show();
            return;
        }

        String[] names = new String[models.size()];
        for (int i = 0; i < models.size(); i++) names[i] = models.get(i).getName();

        AlertDialog.Builder b = new AlertDialog.Builder(this)
            .setTitle("Choose a Model")
            .setItems(names, new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface d, int i) { loadModel(models.get(i), fromChat); }
            })
            .setCancelable(fromChat);
        b.show();
    }

    // ── Server ────────────────────────────────────────────────────────────────

    private void loadModel(final File model, final boolean fromChat) {
        if (fromChat && webView != null) {
            final AlertDialog loading = new AlertDialog.Builder(this)
                .setTitle("Loading Model")
                .setMessage("Loading " + model.getName() + "…\nMay take up to 60 seconds.")
                .setCancelable(false).show();
            new Thread(new Runnable() {
                public void run() {
                    try {
                        killServer(); startServer(model);
                        currentModelName = model.getName();
                        final String name = currentModelName;
                        ui.post(new Runnable() { public void run() {
                            loading.dismiss();
                            String safe = name.replace("\\","\\\\").replace("'","\\'");
                            webView.evaluateJavascript(
                                "if(typeof onModelReady==='function')onModelReady('" + safe + "')", null);
                        }});
                    } catch (final Exception e) {
                        ui.post(new Runnable() { public void run() {
                            loading.dismiss();
                            new AlertDialog.Builder(MainActivity.this)
                                .setTitle("Load Failed")
                                .setMessage(e.getMessage())
                                .setPositiveButton("Try Another", new DialogInterface.OnClickListener() {
                                    public void onClick(DialogInterface d, int w) { pickModel(true); }
                                }).show();
                        }});
                    }
                }
            }).start();
        } else {
            LinearLayout loading = darkLayout();
            loading.setGravity(Gravity.CENTER);
            loading.addView(new ProgressBar(this));
            final TextView txt = label("Loading " + model.getName() + "…", 0xFF94A3B8, 14);
            txt.setGravity(Gravity.CENTER);
            txt.setPadding(0, 24, 0, 0);
            loading.addView(txt);
            setContentView(loading);

            new Thread(new Runnable() {
                public void run() {
                    try {
                        killServer(); startServer(model);
                        currentModelName = model.getName();
                        ui.post(new Runnable() { public void run() { showChat(); }});
                    } catch (final Exception e) {
                        ui.post(new Runnable() { public void run() {
                            txt.setText("Error: " + e.getMessage());
                        }});
                    }
                }
            }).start();
        }
    }

    private void startServer(File model) throws Exception {
        File bd = binDir();
        List<String> cmd = new ArrayList<String>();
        cmd.add(serverBinary().getAbsolutePath());
        cmd.add("-m"); cmd.add(model.getAbsolutePath());
        cmd.add("-c"); cmd.add("4096");
        cmd.add("--host"); cmd.add("127.0.0.1");
        cmd.add("--port"); cmd.add(String.valueOf(SERVER_PORT));
        cmd.add("-n"); cmd.add("-1");

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.environment().put("LD_LIBRARY_PATH", bd.getAbsolutePath());
        pb.redirectErrorStream(true);
        serverProcess = pb.start();

        final Process p = serverProcess;
        new Thread(new Runnable() {
            public void run() {
                try {
                    BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));
                    String line;
                    while ((line = br.readLine()) != null)
                        android.util.Log.d("LlamaServer", line);
                } catch (IOException ignored) {}
            }
        }).start();

        long deadline = System.currentTimeMillis() + 120000;
        while (System.currentTimeMillis() < deadline) {
            if (!isAlive(serverProcess)) throw new Exception("Server process exited");
            try {
                HttpURLConnection c = (HttpURLConnection)
                    new URL("http://127.0.0.1:" + SERVER_PORT + "/health").openConnection();
                c.setConnectTimeout(1000);
                c.setReadTimeout(1000);
                int code = c.getResponseCode();
                c.disconnect();
                if (code == 200) return;
            } catch (Exception ignored) {}
            Thread.sleep(500);
        }
        throw new Exception("Server did not start within 2 minutes");
    }

    private void killServer() {
        if (serverProcess != null) { serverProcess.destroy(); serverProcess = null; }
    }

    private boolean isAlive(Process p) {
        if (p == null) return false;
        try { p.exitValue(); return false; }
        catch (IllegalThreadStateException e) { return true; }
    }

    // ── Chat UI ───────────────────────────────────────────────────────────────

    private void showChat() {
        setContentView(R.layout.activity_main);
        webView = (WebView) findViewById(R.id.webview);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webView.addJavascriptInterface(new Bridge(), "Android");
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("file:///android_asset/index.html");
    }

    class Bridge {
        @JavascriptInterface
        public void changeModel() { ui.post(new Runnable() { public void run() { pickModel(true); }}); }
        @JavascriptInterface
        public String getModelName() { return currentModelName; }
        @JavascriptInterface
        public int getLocalPort() { return SERVER_PORT; }
    }

    // ── Tar.gz Extraction ─────────────────────────────────────────────────────

    interface Progress { void onProgress(int pct); }

    private static final Set<String> WANTED = new HashSet<String>(Arrays.asList(
        "llama-server", "libllama.so", "libllama-common.so", "libmtmd.so",
        "libggml.so", "libggml-base.so"
    ));

    private void extractBinaries(File archive, File dest, Progress cb) throws IOException {
        final long estimated = 200L * 1024 * 1024;
        long extracted = 0;
        byte[] hdr = new byte[512];
        byte[] longName = null;

        GZIPInputStream gz = new GZIPInputStream(
            new BufferedInputStream(new FileInputStream(archive), 65536));
        try {
            while (readBlock(gz, hdr)) {
                if (hdr[0] == 0) break;
                String name = longName != null
                    ? new String(longName, "UTF-8").replace("\0", "").trim()
                    : new String(hdr, 0, 100, "UTF-8").replace("\0", "").trim();
                longName = null;
                char type = (char)(hdr[156] & 0xFF);
                long size = parseOctal(hdr, 124, 12);
                long padded = ((size + 511) / 512) * 512;

                if (type == 'L') {
                    longName = new byte[(int) size];
                    readExact(gz, longName);
                    skipBytes(gz, padded - size);
                    continue;
                }

                String base = new File(name).getName();
                boolean want = WANTED.contains(base) || base.startsWith("libggml-cpu-android");
                if ((type == '0' || type == '\0' || type == 0) && size > 0 && want) {
                    byte[] buf = new byte[65536];
                    long rem = size;
                    FileOutputStream fos = new FileOutputStream(new File(dest, base));
                    try {
                        while (rem > 0) {
                            int r = gz.read(buf, 0, (int) Math.min(buf.length, rem));
                            if (r < 0) break;
                            fos.write(buf, 0, r);
                            rem -= r;
                            extracted += r;
                            cb.onProgress((int)(extracted * 100 / estimated));
                        }
                    } finally { fos.close(); }
                    skipBytes(gz, padded - size);
                } else {
                    skipBytes(gz, padded);
                }
            }
        } finally { gz.close(); }
    }

    private boolean readBlock(InputStream in, byte[] buf) throws IOException {
        int off = 0;
        while (off < buf.length) {
            int n = in.read(buf, off, buf.length - off);
            if (n < 0) return off > 0;
            off += n;
        }
        return true;
    }

    private void readExact(InputStream in, byte[] buf) throws IOException {
        int off = 0;
        while (off < buf.length) {
            int n = in.read(buf, off, buf.length - off);
            if (n < 0) throw new EOFException();
            off += n;
        }
    }

    private void skipBytes(InputStream in, long bytes) throws IOException {
        byte[] buf = new byte[8192];
        long rem = bytes;
        while (rem > 0) {
            int r = in.read(buf, 0, (int) Math.min(buf.length, rem));
            if (r < 0) return;
            rem -= r;
        }
    }

    private long parseOctal(byte[] b, int off, int len) {
        long v = 0;
        for (int i = off; i < off + len; i++)
            if (b[i] >= '0' && b[i] <= '7') v = v * 8 + (b[i] - '0');
        return v;
    }

    private HttpURLConnection openConn(URL url) throws IOException {
        for (int i = 0; i < 10; i++) {
            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            c.setInstanceFollowRedirects(false);
            c.setConnectTimeout(20000);
            c.setReadTimeout(60000);
            int code = c.getResponseCode();
            if (code == 301 || code == 302 || code == 303 || code == 307 || code == 308) {
                String loc = c.getHeaderField("Location");
                c.disconnect();
                url = new URL(loc);
            } else return c;
        }
        throw new IOException("Too many redirects");
    }

    private LinearLayout darkLayout() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setBackgroundColor(0xFF0f1117);
        return l;
    }

    private TextView label(String text, int color, int sp) {
        TextView tv = new TextView(this);
        tv.setText(text); tv.setTextColor(color); tv.setTextSize(sp);
        return tv;
    }

    private Button accentButton(String text) {
        Button b = new Button(this);
        b.setText(text); b.setBackgroundColor(0xFF6366f1); b.setTextColor(0xFFFFFFFF);
        return b;
    }
}
