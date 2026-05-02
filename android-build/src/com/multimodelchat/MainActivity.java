package com.multimodelchat;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.DocumentsContract;
import android.provider.Settings;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileFilter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class MainActivity extends Activity {

    private static final int SERVER_PORT  = 8080;
    private static final int REQUEST_FOLDER  = 1;
    private static final int REQUEST_STORAGE = 2;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private WebView webView;
    private Process serverProcess;
    private String currentModelName = "";
    private String lastServerLog    = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
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

    @Override
    protected void onResume() {
        super.onResume();
        js("if(typeof onAppResume==='function')onAppResume()");
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_STORAGE && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            js("onStorageGranted()");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_FOLDER && resultCode == RESULT_OK && data != null) {
            String path = uriToPath(data.getData());
            if (path != null) {
                js("onFolderSelected('" + path.replace("'", "\\'") + "')");
            } else {
                js("onFolderSelectFailed()");
            }
        }
    }

    private String uriToPath(Uri uri) {
        try {
            String docId = DocumentsContract.getTreeDocumentId(uri);
            String[] parts = docId.split(":", 2);
            if (parts.length == 2) {
                if ("primary".equals(parts[0])) {
                    return Environment.getExternalStorageDirectory().getAbsolutePath() + "/" + parts[1];
                } else {
                    return "/storage/" + parts[0] + "/" + parts[1];
                }
            }
            return Environment.getExternalStorageDirectory().getAbsolutePath();
        } catch (Exception e) {
            return null;
        }
    }

    // Binaries live in nativeLibraryDir — installed by Android from APK lib/arm64-v8a/,
    // always executable regardless of Samsung W^X policy.
    private File nativeLibDir() {
        return new File(getApplicationInfo().nativeLibraryDir);
    }

    private File serverBinary() {
        return new File(nativeLibDir(), "libllama_server.so");
    }

    private void js(final String code) {
        ui.post(new Runnable() {
            public void run() {
                if (webView != null) webView.evaluateJavascript(code, null);
            }
        });
    }

    // ── Bridge ────────────────────────────────────────────────────────────────

    class Bridge {
        @JavascriptInterface
        public String getStatus() {
            if (!serverBinary().exists()) return "needs_setup";
            if (currentModelName.isEmpty()) return "needs_model";
            return "ready:" + currentModelName;
        }

        @JavascriptInterface
        public String getDefaultModelsPath() {
            File dl = new File(Environment.getExternalStorageDirectory(), "Download");
            if (dl.isDirectory()) return dl.getAbsolutePath();
            File ext = getExternalFilesDir(null);
            if (ext != null) return ext.getAbsolutePath();
            return Environment.getExternalStorageDirectory().getAbsolutePath();
        }

        @JavascriptInterface
        public String getModelList(final String folderPath) {
            File dir = new File(folderPath);
            if (!dir.isDirectory()) return "";
            File[] files = dir.listFiles(new FileFilter() {
                public boolean accept(File f) {
                    return f.isFile() && f.getName().toLowerCase().endsWith(".gguf");
                }
            });
            if (files == null || files.length == 0) return "";
            Arrays.sort(files);
            StringBuilder sb = new StringBuilder();
            for (File f : files) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(f.getName()).append("|").append(f.getAbsolutePath());
            }
            return sb.toString();
        }

        @JavascriptInterface
        public void loadModel(final String path) {
            final String name = new File(path).getName();
            js("onModelLoading('" + name.replace("'", "\\'") + "')");
            new Thread(new Runnable() {
                public void run() {
                    try {
                        killServer();
                        startServer(new File(path));
                        currentModelName = name;
                        js("onModelReady('" + name.replace("'", "\\'") + "')");
                    } catch (final Exception e) {
                        String raw = e.getMessage() != null ? e.getMessage() : "Unknown error";
                        String msg = raw.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ");
                        js("onModelError('" + msg + "')");
                    }
                }
            }).start();
        }

        @JavascriptInterface
        public void changeModel() {
            killServer();
            currentModelName = "";
            js("onShowModelPicker()");
        }

        @JavascriptInterface
        public String getStorageStatus() {
            if (Build.VERSION.SDK_INT >= 30) {
                try {
                    java.lang.reflect.Method m = Environment.class.getMethod("isExternalStorageManager");
                    Boolean r = (Boolean) m.invoke(null);
                    return (r != null && r) ? "ok" : "needs_all_files";
                } catch (Exception e) {
                    return "ok";
                }
            } else if (Build.VERSION.SDK_INT >= 23) {
                int perm = checkSelfPermission(android.Manifest.permission.READ_EXTERNAL_STORAGE);
                return perm == PackageManager.PERMISSION_GRANTED ? "ok" : "needs_request";
            }
            return "ok";
        }

        @JavascriptInterface
        public void requestStorageAccess() {
            ui.post(new Runnable() {
                public void run() {
                    if (Build.VERSION.SDK_INT >= 30) {
                        try {
                            Intent i = new Intent(
                                "android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION",
                                Uri.parse("package:" + getPackageName()));
                            startActivity(i);
                        } catch (Exception e) {
                            try {
                                startActivity(new Intent(
                                    "android.settings.MANAGE_ALL_FILES_ACCESS_PERMISSION"));
                            } catch (Exception e2) {
                                startActivity(new Intent(Settings.ACTION_SETTINGS));
                            }
                        }
                    } else {
                        requestPermissions(
                            new String[]{android.Manifest.permission.READ_EXTERNAL_STORAGE},
                            REQUEST_STORAGE);
                    }
                }
            });
        }

        @JavascriptInterface
        public void browseFolders() {
            ui.post(new Runnable() {
                public void run() {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
                    startActivityForResult(intent, REQUEST_FOLDER);
                }
            });
        }

        @JavascriptInterface
        public boolean pathExists(String path) {
            return new File(path).exists();
        }

        @JavascriptInterface
        public String findAllGgufFiles() {
            StringBuilder sb = new StringBuilder();
            android.database.Cursor cursor = null;
            try {
                String[] proj = {
                    android.provider.MediaStore.Files.FileColumns.DISPLAY_NAME,
                    android.provider.MediaStore.Files.FileColumns.DATA
                };
                String sel = android.provider.MediaStore.Files.FileColumns.DISPLAY_NAME + " LIKE ?";
                android.net.Uri vol = android.provider.MediaStore.Files.getContentUri("external");
                cursor = getContentResolver().query(vol, proj, sel, new String[]{"%.gguf"},
                    android.provider.MediaStore.Files.FileColumns.DISPLAY_NAME + " ASC");
                if (cursor != null) {
                    while (cursor.moveToNext()) {
                        String name = cursor.getString(0);
                        String path = cursor.getString(1);
                        if (name != null && path != null && !path.isEmpty()) {
                            if (sb.length() > 0) sb.append("\n");
                            sb.append(name).append("|").append(path);
                        }
                    }
                }
            } catch (Exception e) {
                android.util.Log.e("MediaStore", "findAllGgufFiles: " + e.getMessage());
            } finally {
                if (cursor != null) cursor.close();
            }
            return sb.toString();
        }

        @JavascriptInterface
        public String getStorageRoots() {
            StringBuilder sb = new StringBuilder();
            File ext = Environment.getExternalStorageDirectory();
            sb.append("getExternalStorageDirectory: ")
              .append(ext != null ? ext.getAbsolutePath() : "null")
              .append(" exists=").append(ext != null && ext.exists()).append("\n");
            File[] dirs = getExternalFilesDirs(null);
            if (dirs != null) {
                for (int i = 0; i < dirs.length; i++) {
                    if (dirs[i] != null) {
                        sb.append("externalFilesDir[").append(i).append("]: ")
                          .append(dirs[i].getAbsolutePath())
                          .append(" exists=").append(dirs[i].exists()).append("\n");
                    }
                }
            }
            String[] probes = {
                "/storage/emulated/0", "/storage/emulated/0/Models",
                "/storage/emulated/0/Download", "/sdcard", "/sdcard/Models"
            };
            for (String p : probes) {
                File f = new File(p);
                sb.append("probe ").append(p).append(": exists=").append(f.exists()).append("\n");
            }
            sb.append("nativeLibDir: ").append(nativeLibDir().getAbsolutePath()).append("\n");
            sb.append("llama_server exists: ").append(serverBinary().exists()).append("\n");
            return sb.toString();
        }

        @JavascriptInterface
        public String debugPath(String path) {
            StringBuilder sb = new StringBuilder();
            try {
                File f = new File(path);
                sb.append("path: ").append(path).append("\n");
                sb.append("exists: ").append(f.exists()).append("\n");
                sb.append("isDir: ").append(f.isDirectory()).append("\n");
                sb.append("canRead: ").append(f.canRead()).append("\n");
                if (f.isDirectory()) {
                    File[] all = f.listFiles();
                    sb.append("listFiles: ").append(all == null ? "null" : all.length + " items").append("\n");
                    if (all != null) {
                        int gguf = 0;
                        for (File ff : all) {
                            if (ff.getName().toLowerCase().endsWith(".gguf")) gguf++;
                        }
                        sb.append("gguf count: ").append(gguf).append("\n");
                    }
                }
                if (Build.VERSION.SDK_INT >= 30) {
                    try {
                        java.lang.reflect.Method m = Environment.class.getMethod("isExternalStorageManager");
                        sb.append("storageManager: ").append(m.invoke(null)).append("\n");
                    } catch (Exception e2) {
                        sb.append("storageManager: reflection failed\n");
                    }
                }
            } catch (Exception e) {
                sb.append("error: ").append(e.getMessage()).append("\n");
            }
            return sb.toString();
        }

        @JavascriptInterface
        public String getLastError() { return lastServerLog; }

        @JavascriptInterface
        public String getModelName() { return currentModelName; }

        @JavascriptInterface
        public int getLocalPort() { return SERVER_PORT; }
    }

    // ── Server ────────────────────────────────────────────────────────────────

    private void startServer(File model) throws Exception {
        File nld = nativeLibDir();
        List<String> cmd = new ArrayList<String>();
        cmd.add(serverBinary().getAbsolutePath());
        cmd.add("-m"); cmd.add(model.getAbsolutePath());
        cmd.add("-c"); cmd.add("4096");
        cmd.add("--host"); cmd.add("127.0.0.1");
        cmd.add("--port"); cmd.add(String.valueOf(SERVER_PORT));
        cmd.add("-n"); cmd.add("-1");

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.environment().put("LD_LIBRARY_PATH", nld.getAbsolutePath());
        pb.redirectErrorStream(true);
        serverProcess = pb.start();

        final Process p = serverProcess;
        final StringBuilder logBuf = new StringBuilder();
        new Thread(new Runnable() {
            public void run() {
                try {
                    BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));
                    String line;
                    while ((line = br.readLine()) != null) {
                        android.util.Log.d("LlamaServer", line);
                        synchronized (logBuf) {
                            logBuf.append(line).append("\n");
                            if (logBuf.length() > 4000) logBuf.delete(0, logBuf.length() - 4000);
                        }
                    }
                } catch (IOException ignored) {}
            }
        }).start();

        long deadline = System.currentTimeMillis() + 120000;
        while (System.currentTimeMillis() < deadline) {
            if (!isAlive(serverProcess)) {
                Thread.sleep(300);
                synchronized (logBuf) { lastServerLog = logBuf.toString().trim(); }
                throw new Exception("Server exited.\n" + lastServerLog);
            }
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
        synchronized (logBuf) { lastServerLog = logBuf.toString().trim(); }
        throw new Exception("Server did not start within 2 minutes.\n" + lastServerLog);
    }

    private void killServer() {
        if (serverProcess != null) { serverProcess.destroy(); serverProcess = null; }
    }

    private boolean isAlive(Process p) {
        if (p == null) return false;
        try { p.exitValue(); return false; }
        catch (IllegalThreadStateException e) { return true; }
    }
}
