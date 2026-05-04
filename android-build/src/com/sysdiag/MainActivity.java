package com.sysdiag;

import android.app.Activity;
import android.app.ActivityManager;
import android.bluetooth.BluetoothAdapter;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.LocationManager;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.opengl.GLES10;
import android.opengl.GLES20;
import android.opengl.GLES30;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Debug;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.StatFs;
import android.os.SystemClock;
import android.provider.Settings;
import android.telephony.TelephonyManager;
import android.util.DisplayMetrics;
import android.view.Display;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

import javax.microedition.khronos.egl.EGL10;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.egl.EGLContext;
import javax.microedition.khronos.egl.EGLDisplay;
import javax.microedition.khronos.egl.EGLSurface;

public class MainActivity extends Activity {

    private final Handler ui = new Handler(Looper.getMainLooper());
    private WebView webView;
    private SensorManager sensorManager;

    // Live sensor stream state — values come in on the main thread,
    // are read by the WebView (JS bridge) thread.
    private final java.util.concurrent.ConcurrentHashMap<Integer, float[]> latestValues =
        new java.util.concurrent.ConcurrentHashMap<Integer, float[]>();
    private final java.util.concurrent.ConcurrentHashMap<Integer, Long> latestTimestamp =
        new java.util.concurrent.ConcurrentHashMap<Integer, Long>();
    private final java.util.concurrent.ConcurrentHashMap<Integer, Integer> latestAccuracy =
        new java.util.concurrent.ConcurrentHashMap<Integer, Integer>();
    private SensorEventListener streamListener;
    private boolean streamActive = false;

    // GPU info captured once on a temporary EGL context
    private String glRenderer = "Unknown";
    private String glVendor = "Unknown";
    private String glVersion = "Unknown";
    private String glExtensions = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        new Thread(new Runnable() { public void run() { captureGpuInfo(); } }).start();

        webView = (WebView) findViewById(R.id.webview);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        webView.addJavascriptInterface(new Bridge(), "Native");
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onPause() { super.onPause(); stopSensorStream(); }

    @Override
    protected void onResume() { super.onResume(); /* JS will restart if on sensors tab */ }

    @Override
    protected void onDestroy() { super.onDestroy(); stopSensorStream(); }

    // ─── Sensor streaming ─────────────────────────────────────────────────────

    private void startSensorStream() {
        if (streamActive) return;
        streamActive = true;
        streamListener = new SensorEventListener() {
            public void onSensorChanged(SensorEvent e) {
                int n = e.values.length;
                float[] copy = new float[n];
                System.arraycopy(e.values, 0, copy, 0, n);
                int t = e.sensor.getType();
                latestValues.put(t, copy);
                latestTimestamp.put(t, e.timestamp);
            }
            public void onAccuracyChanged(Sensor s, int a) {
                latestAccuracy.put(s.getType(), a);
            }
        };
        for (Sensor s : sensorManager.getSensorList(Sensor.TYPE_ALL)) {
            // Skip one-shot/special-reporting sensors that won't stream
            int rep = (Build.VERSION.SDK_INT >= 21) ? s.getReportingMode() : 0;
            if (rep == 2 /* REPORTING_MODE_ONE_SHOT */) continue;
            sensorManager.registerListener(streamListener, s, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    private void stopSensorStream() {
        if (!streamActive) return;
        streamActive = false;
        if (streamListener != null) {
            try { sensorManager.unregisterListener(streamListener); } catch (Exception ignored) {}
            streamListener = null;
        }
        latestValues.clear();
        latestTimestamp.clear();
        latestAccuracy.clear();
    }

    // ─── JavaScript bridge ────────────────────────────────────────────────────

    public class Bridge {
        @JavascriptInterface
        public String getOverview() {
            try {
                JSONObject o = new JSONObject();
                o.put("device", Build.MANUFACTURER + " " + Build.MODEL);
                o.put("brand", Build.BRAND);
                o.put("product", Build.PRODUCT);
                o.put("board", Build.BOARD);
                o.put("hardware", Build.HARDWARE);
                o.put("androidRelease", Build.VERSION.RELEASE);
                o.put("sdkInt", Build.VERSION.SDK_INT);
                o.put("codename", Build.VERSION.CODENAME);
                o.put("incremental", Build.VERSION.INCREMENTAL);
                o.put("securityPatch", Build.VERSION.SECURITY_PATCH);
                o.put("bootloader", Build.BOOTLOADER);
                o.put("fingerprint", Build.FINGERPRINT);
                o.put("kernel", System.getProperty("os.version"));
                o.put("uptimeMs", SystemClock.elapsedRealtime());
                o.put("locale", Locale.getDefault().toString());
                o.put("timezone", TimeZone.getDefault().getID());
                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getCpu() {
            try {
                JSONObject o = new JSONObject();
                int cores = Runtime.getRuntime().availableProcessors();
                o.put("cores", cores);
                o.put("supportedAbis", new JSONArray(Build.SUPPORTED_ABIS));
                o.put("supported32", new JSONArray(Build.SUPPORTED_32_BIT_ABIS));
                o.put("supported64", new JSONArray(Build.SUPPORTED_64_BIT_ABIS));
                o.put("arch", System.getProperty("os.arch"));

                // /proc/cpuinfo (model, hardware, features)
                Map<String,String> cpuinfo = parseCpuinfo();
                o.put("hardware", cpuinfo.get("Hardware"));
                o.put("processor", cpuinfo.get("Processor"));
                o.put("features", cpuinfo.get("Features"));
                o.put("implementer", cpuinfo.get("CPU implementer"));
                o.put("part", cpuinfo.get("CPU part"));
                o.put("variant", cpuinfo.get("CPU variant"));
                o.put("revision", cpuinfo.get("CPU revision"));

                // Per-core frequencies & governors
                JSONArray coreData = new JSONArray();
                for (int i = 0; i < cores; i++) {
                    JSONObject c = new JSONObject();
                    String base = "/sys/devices/system/cpu/cpu" + i + "/cpufreq/";
                    c.put("index", i);
                    c.put("cur", readLong(base + "scaling_cur_freq"));
                    c.put("min", readLong(base + "cpuinfo_min_freq"));
                    c.put("max", readLong(base + "cpuinfo_max_freq"));
                    c.put("governor", readString(base + "scaling_governor"));
                    c.put("driver", readString(base + "scaling_driver"));
                    coreData.put(c);
                }
                o.put("perCore", coreData);

                // 1-min load average
                String loadavg = readString("/proc/loadavg");
                if (loadavg != null) o.put("loadavg", loadavg.trim());

                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getMemory() {
            try {
                JSONObject o = new JSONObject();
                ActivityManager am = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
                ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
                am.getMemoryInfo(mi);
                o.put("totalRam", mi.totalMem);
                o.put("availRam", mi.availMem);
                o.put("usedRam", mi.totalMem - mi.availMem);
                o.put("threshold", mi.threshold);
                o.put("lowMemory", mi.lowMemory);

                // /proc/meminfo for swap, cached, buffers
                Map<String,Long> mem = parseMeminfo();
                o.put("memTotal", val(mem, "MemTotal"));
                o.put("memFree", val(mem, "MemFree"));
                o.put("memAvail", val(mem, "MemAvailable"));
                o.put("buffers", val(mem, "Buffers"));
                o.put("cached", val(mem, "Cached"));
                o.put("swapTotal", val(mem, "SwapTotal"));
                o.put("swapFree", val(mem, "SwapFree"));
                o.put("swapCached", val(mem, "SwapCached"));
                o.put("vmallocTotal", val(mem, "VmallocTotal"));

                // Storage: internal & external
                JSONArray storage = new JSONArray();
                storage.put(statForPath(Environment.getDataDirectory(), "Internal /data"));
                storage.put(statForPath(Environment.getRootDirectory(), "System /system"));
                File ext = Environment.getExternalStorageDirectory();
                if (ext != null) storage.put(statForPath(ext, "External " + ext.getAbsolutePath()));
                o.put("storage", storage);

                // App heap stats
                JSONObject heap = new JSONObject();
                Runtime r = Runtime.getRuntime();
                heap.put("max", r.maxMemory());
                heap.put("total", r.totalMemory());
                heap.put("free", r.freeMemory());
                heap.put("used", r.totalMemory() - r.freeMemory());
                heap.put("nativeAlloc", Debug.getNativeHeapAllocatedSize());
                heap.put("nativeSize", Debug.getNativeHeapSize());
                heap.put("nativeFree", Debug.getNativeHeapFreeSize());
                o.put("heap", heap);

                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getBattery() {
            try {
                JSONObject o = new JSONObject();
                IntentFilter f = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
                Intent i = registerReceiver(null, f);
                if (i == null) { o.put("error", "no battery info"); return o.toString(); }

                int level = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                int scale = i.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
                int status = i.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
                int plugged = i.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1);
                int health = i.getIntExtra(BatteryManager.EXTRA_HEALTH, -1);
                int temp = i.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1);
                int voltage = i.getIntExtra(BatteryManager.EXTRA_VOLTAGE, -1);
                String tech = i.getStringExtra(BatteryManager.EXTRA_TECHNOLOGY);

                o.put("percent", scale > 0 ? level * 100.0 / scale : -1);
                o.put("level", level);
                o.put("scale", scale);
                o.put("status", batteryStatusName(status));
                o.put("plugged", batteryPluggedName(plugged));
                o.put("health", batteryHealthName(health));
                o.put("temperatureC", temp / 10.0);
                o.put("voltageV", voltage / 1000.0);
                o.put("technology", tech);

                BatteryManager bm = (BatteryManager) getSystemService(Context.BATTERY_SERVICE);
                if (bm != null && Build.VERSION.SDK_INT >= 21) {
                    o.put("currentNowUA", bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW));
                    o.put("currentAvgUA", bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_AVERAGE));
                    o.put("capacityPct", bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY));
                    o.put("chargeCounterUAh", bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CHARGE_COUNTER));
                    if (Build.VERSION.SDK_INT >= 26) {
                        o.put("energyCounterNWh", bm.getLongProperty(BatteryManager.BATTERY_PROPERTY_ENERGY_COUNTER));
                    }
                }

                // Thermal zones — read every zone in /sys/class/thermal
                JSONArray zones = new JSONArray();
                File thermalDir = new File("/sys/class/thermal");
                File[] zd = thermalDir.listFiles();
                if (zd != null) {
                    java.util.Arrays.sort(zd);
                    for (File z : zd) {
                        if (!z.getName().startsWith("thermal_zone")) continue;
                        JSONObject zo = new JSONObject();
                        zo.put("zone", z.getName());
                        zo.put("type", readString(new File(z, "type").getAbsolutePath()));
                        Long t = readLong(new File(z, "temp").getAbsolutePath());
                        if (t != null) zo.put("tempC", t > 1000 ? t / 1000.0 : t.doubleValue());
                        zones.put(zo);
                    }
                }
                o.put("thermalZones", zones);

                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getDisplay() {
            try {
                JSONObject o = new JSONObject();
                WindowManager wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
                Display d = wm.getDefaultDisplay();
                DisplayMetrics m = new DisplayMetrics();
                d.getRealMetrics(m);
                o.put("widthPx", m.widthPixels);
                o.put("heightPx", m.heightPixels);
                o.put("density", m.density);
                o.put("densityDpi", m.densityDpi);
                o.put("xdpi", m.xdpi);
                o.put("ydpi", m.ydpi);
                o.put("scaledDensity", m.scaledDensity);
                o.put("refreshRate", d.getRefreshRate());
                o.put("rotation", d.getRotation());
                o.put("name", d.getName());
                if (Build.VERSION.SDK_INT >= 23) {
                    Display.Mode[] modes = d.getSupportedModes();
                    JSONArray ma = new JSONArray();
                    for (Display.Mode mode : modes) {
                        JSONObject mo = new JSONObject();
                        mo.put("id", mode.getModeId());
                        mo.put("w", mode.getPhysicalWidth());
                        mo.put("h", mode.getPhysicalHeight());
                        mo.put("hz", mode.getRefreshRate());
                        ma.put(mo);
                    }
                    o.put("modes", ma);
                }

                JSONObject gl = new JSONObject();
                gl.put("renderer", glRenderer);
                gl.put("vendor", glVendor);
                gl.put("version", glVersion);
                gl.put("extensions", glExtensions);
                o.put("gpu", gl);

                Configuration cfg = getResources().getConfiguration();
                o.put("nightMode", (cfg.uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES);
                o.put("fontScale", cfg.fontScale);

                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getSensors() {
            try {
                JSONArray arr = new JSONArray();
                List<Sensor> list = sensorManager.getSensorList(Sensor.TYPE_ALL);
                for (Sensor s : list) {
                    JSONObject o = new JSONObject();
                    o.put("name", s.getName());
                    o.put("vendor", s.getVendor());
                    o.put("type", s.getStringType());
                    o.put("typeId", s.getType());
                    o.put("version", s.getVersion());
                    o.put("power", s.getPower());
                    o.put("range", s.getMaximumRange());
                    o.put("resolution", s.getResolution());
                    o.put("minDelayUs", s.getMinDelay());
                    if (Build.VERSION.SDK_INT >= 21) {
                        o.put("maxDelayUs", s.getMaxDelay());
                        o.put("reporting", s.getReportingMode());
                    }
                    arr.put(o);
                }
                return arr.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public void startStream() {
            ui.post(new Runnable() { public void run() { startSensorStream(); }});
        }

        @JavascriptInterface
        public void stopStream() {
            ui.post(new Runnable() { public void run() { stopSensorStream(); }});
        }

        @JavascriptInterface
        public String pollStream() {
            try {
                JSONObject o = new JSONObject();
                for (Integer k : latestValues.keySet()) {
                    JSONObject e = new JSONObject();
                    float[] v = latestValues.get(k);
                    if (v == null) continue;
                    JSONArray a = new JSONArray();
                    for (float f : v) a.put((double) f);
                    e.put("v", a);
                    Long t = latestTimestamp.get(k);
                    if (t != null) e.put("t", (double) t.longValue());
                    Integer acc = latestAccuracy.get(k);
                    if (acc != null) e.put("a", acc.intValue());
                    o.put(String.valueOf(k), e);
                }
                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String readSensorOnce(final int typeId) {
            // Best-effort one-shot read with 800 ms timeout
            try {
                Sensor s = sensorManager.getDefaultSensor(typeId);
                if (s == null) return "{\"error\":\"sensor not present\"}";
                final float[] vals = new float[6];
                final boolean[] got = {false};
                final Object lock = new Object();
                SensorEventListener l = new SensorEventListener() {
                    public void onSensorChanged(SensorEvent e) {
                        int n = Math.min(e.values.length, vals.length);
                        for (int i = 0; i < n; i++) vals[i] = e.values[i];
                        synchronized (lock) { got[0] = true; lock.notifyAll(); }
                    }
                    public void onAccuracyChanged(Sensor s, int a) {}
                };
                sensorManager.registerListener(l, s, SensorManager.SENSOR_DELAY_FASTEST);
                synchronized (lock) {
                    long start = System.currentTimeMillis();
                    while (!got[0] && System.currentTimeMillis() - start < 800) {
                        try { lock.wait(50); } catch (InterruptedException ignored) {}
                    }
                }
                sensorManager.unregisterListener(l);
                JSONObject o = new JSONObject();
                JSONArray a = new JSONArray();
                for (float v : vals) a.put(v);
                o.put("values", a);
                o.put("ok", got[0]);
                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getNetwork() {
            try {
                JSONObject o = new JSONObject();
                ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                if (cm != null && Build.VERSION.SDK_INT >= 23) {
                    Network active = cm.getActiveNetwork();
                    if (active != null) {
                        NetworkCapabilities caps = cm.getNetworkCapabilities(active);
                        if (caps != null) {
                            o.put("downstreamKbps", caps.getLinkDownstreamBandwidthKbps());
                            o.put("upstreamKbps", caps.getLinkUpstreamBandwidthKbps());
                            o.put("wifi", caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI));
                            o.put("cellular", caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR));
                            o.put("ethernet", caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
                            o.put("vpn", caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN));
                            o.put("validated", caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED));
                            o.put("metered", !caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED));
                        }
                        LinkProperties lp = cm.getLinkProperties(active);
                        if (lp != null) {
                            o.put("interface", lp.getInterfaceName());
                            JSONArray dns = new JSONArray();
                            for (InetAddress a : lp.getDnsServers()) dns.put(a.getHostAddress());
                            o.put("dns", dns);
                        }
                    }
                }

                WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if (wm != null) {
                    JSONObject wf = new JSONObject();
                    wf.put("enabled", wm.isWifiEnabled());
                    WifiInfo wi = wm.getConnectionInfo();
                    if (wi != null) {
                        wf.put("rssi", wi.getRssi());
                        wf.put("linkSpeedMbps", wi.getLinkSpeed());
                        if (Build.VERSION.SDK_INT >= 21) wf.put("frequencyMhz", wi.getFrequency());
                        wf.put("ssid", wi.getSSID());
                        wf.put("bssid", wi.getBSSID());
                        wf.put("hiddenSsid", wi.getHiddenSSID());
                        if (Build.VERSION.SDK_INT >= 29) wf.put("standard", wi.getWifiStandard());
                    }
                    o.put("wifi", wf);
                }

                TelephonyManager tm = (TelephonyManager) getSystemService(Context.TELEPHONY_SERVICE);
                if (tm != null) {
                    JSONObject tel = new JSONObject();
                    tel.put("operator", tm.getNetworkOperatorName());
                    tel.put("country", tm.getNetworkCountryIso());
                    tel.put("simState", tm.getSimState());
                    if (Build.VERSION.SDK_INT >= 24) tel.put("dataNetworkType", tm.getDataNetworkType());
                    tel.put("phoneType", tm.getPhoneType());
                    o.put("telephony", tel);
                }

                JSONArray ifs = new JSONArray();
                for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                    JSONObject n = new JSONObject();
                    n.put("name", ni.getName());
                    n.put("display", ni.getDisplayName());
                    n.put("up", ni.isUp());
                    n.put("loopback", ni.isLoopback());
                    n.put("mtu", ni.getMTU());
                    JSONArray addrs = new JSONArray();
                    for (InetAddress a : Collections.list(ni.getInetAddresses()))
                        addrs.put(a.getHostAddress());
                    n.put("addresses", addrs);
                    byte[] mac = ni.getHardwareAddress();
                    if (mac != null) {
                        StringBuilder sb = new StringBuilder();
                        for (int j = 0; j < mac.length; j++) {
                            sb.append(String.format("%02x", mac[j]));
                            if (j < mac.length - 1) sb.append(':');
                        }
                        n.put("mac", sb.toString());
                    }
                    ifs.put(n);
                }
                o.put("interfaces", ifs);

                BluetoothAdapter ba = BluetoothAdapter.getDefaultAdapter();
                if (ba != null) {
                    JSONObject bt = new JSONObject();
                    bt.put("present", true);
                    bt.put("enabled", ba.isEnabled());
                    bt.put("name", ba.getName());
                    o.put("bluetooth", bt);
                } else {
                    o.put("bluetooth", new JSONObject().put("present", false));
                }

                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String getFeatures() {
            try {
                PackageManager pm = getPackageManager();
                JSONArray arr = new JSONArray();
                android.content.pm.FeatureInfo[] feats = pm.getSystemAvailableFeatures();
                if (feats != null) {
                    for (android.content.pm.FeatureInfo f : feats)
                        if (f.name != null) arr.put(f.name);
                }
                JSONObject o = new JSONObject();
                o.put("features", arr);
                o.put("appsInstalled", pm.getInstalledPackages(0).size());
                LocationManager lm = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
                if (lm != null) {
                    JSONArray providers = new JSONArray(lm.getAllProviders());
                    o.put("locationProviders", providers);
                }
                return o.toString();
            } catch (Exception e) { return errorJson(e); }
        }

        @JavascriptInterface
        public String benchmarkCpuInt(int millis) {
            // Pure-integer pseudo-random hashing — counts ops per ms
            long deadline = System.nanoTime() + millis * 1_000_000L;
            long x = 0x9E3779B97F4A7C15L;
            long ops = 0;
            while (System.nanoTime() < deadline) {
                for (int i = 0; i < 4096; i++) {
                    x ^= x << 13;
                    x ^= x >>> 7;
                    x ^= x << 17;
                }
                ops += 4096;
            }
            return resultJson("ops", ops, "ms", millis, "checksum", x);
        }

        @JavascriptInterface
        public String benchmarkCpuFloat(int millis) {
            long deadline = System.nanoTime() + millis * 1_000_000L;
            double a = 1.000001, b = 0.999999, c = 0;
            long ops = 0;
            while (System.nanoTime() < deadline) {
                for (int i = 0; i < 4096; i++) {
                    c = c * a + b;
                    c = Math.sqrt(c * c + 1.0);
                }
                ops += 8192;
            }
            return resultJson("ops", ops, "ms", millis, "checksum", c);
        }

        @JavascriptInterface
        public String benchmarkMemory(int sizeMb, int iterations) {
            int n = sizeMb * 1024 * 1024 / 4;
            int[] buf = new int[n];
            for (int i = 0; i < n; i++) buf[i] = i;
            long t0 = System.nanoTime();
            long sum = 0;
            for (int it = 0; it < iterations; it++)
                for (int i = 0; i < n; i++) sum += buf[i];
            long ns = System.nanoTime() - t0;
            long bytes = (long) n * 4 * iterations;
            double mbps = bytes / 1048576.0 / (ns / 1e9);
            return resultJson("mbPerSec", mbps, "bytes", bytes, "ns", ns, "checksum", sum);
        }
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private static String errorJson(Exception e) {
        try {
            JSONObject o = new JSONObject();
            o.put("error", e.getClass().getSimpleName() + ": " + e.getMessage());
            return o.toString();
        } catch (Exception ignored) { return "{\"error\":\"unknown\"}"; }
    }

    private static String resultJson(Object... kv) {
        try {
            JSONObject o = new JSONObject();
            for (int i = 0; i + 1 < kv.length; i += 2) o.put((String) kv[i], kv[i + 1]);
            return o.toString();
        } catch (Exception e) { return errorJson(e); }
    }

    private static Long readLong(String path) {
        String v = readString(path);
        if (v == null) return null;
        try { return Long.parseLong(v.trim()); } catch (NumberFormatException e) { return null; }
    }

    private static String readString(String path) {
        File f = new File(path);
        if (!f.exists() || !f.canRead()) return null;
        try (BufferedReader br = new BufferedReader(new FileReader(f))) {
            StringBuilder sb = new StringBuilder();
            char[] buf = new char[256];
            int n;
            while ((n = br.read(buf)) > 0) {
                sb.append(buf, 0, n);
                if (sb.length() > 16384) break;
            }
            return sb.toString();
        } catch (Exception e) { return null; }
    }

    private static Map<String,String> parseCpuinfo() {
        Map<String,String> m = new HashMap<>();
        String s = readString("/proc/cpuinfo");
        if (s == null) return m;
        for (String line : s.split("\n")) {
            int idx = line.indexOf(':');
            if (idx <= 0) continue;
            String k = line.substring(0, idx).trim();
            String v = line.substring(idx + 1).trim();
            if (!m.containsKey(k)) m.put(k, v);
        }
        return m;
    }

    private static Map<String,Long> parseMeminfo() {
        Map<String,Long> m = new HashMap<>();
        String s = readString("/proc/meminfo");
        if (s == null) return m;
        for (String line : s.split("\n")) {
            int idx = line.indexOf(':');
            if (idx <= 0) continue;
            String k = line.substring(0, idx).trim();
            String v = line.substring(idx + 1).trim().replace(" kB", "");
            try { m.put(k, Long.parseLong(v) * 1024); } catch (NumberFormatException ignored) {}
        }
        return m;
    }

    private static Long val(Map<String,Long> m, String k) { return m.get(k); }

    private static JSONObject statForPath(File path, String label) throws Exception {
        JSONObject o = new JSONObject();
        o.put("label", label);
        o.put("path", path.getAbsolutePath());
        try {
            StatFs sf = new StatFs(path.getAbsolutePath());
            long total = (long) sf.getBlockCountLong() * sf.getBlockSizeLong();
            long free  = (long) sf.getAvailableBlocksLong() * sf.getBlockSizeLong();
            o.put("total", total);
            o.put("free", free);
            o.put("used", total - free);
        } catch (Exception e) {
            o.put("error", e.getMessage());
        }
        return o;
    }

    private static String batteryStatusName(int s) {
        switch (s) {
            case BatteryManager.BATTERY_STATUS_CHARGING: return "Charging";
            case BatteryManager.BATTERY_STATUS_DISCHARGING: return "Discharging";
            case BatteryManager.BATTERY_STATUS_FULL: return "Full";
            case BatteryManager.BATTERY_STATUS_NOT_CHARGING: return "Not charging";
            default: return "Unknown";
        }
    }

    private static String batteryPluggedName(int p) {
        if (p == 0) return "On battery";
        StringBuilder sb = new StringBuilder();
        if ((p & BatteryManager.BATTERY_PLUGGED_AC) != 0) sb.append("AC ");
        if ((p & BatteryManager.BATTERY_PLUGGED_USB) != 0) sb.append("USB ");
        if ((p & BatteryManager.BATTERY_PLUGGED_WIRELESS) != 0) sb.append("Wireless ");
        return sb.length() == 0 ? "Plugged" : sb.toString().trim();
    }

    private static String batteryHealthName(int h) {
        switch (h) {
            case BatteryManager.BATTERY_HEALTH_GOOD: return "Good";
            case BatteryManager.BATTERY_HEALTH_OVERHEAT: return "Overheat";
            case BatteryManager.BATTERY_HEALTH_DEAD: return "Dead";
            case BatteryManager.BATTERY_HEALTH_OVER_VOLTAGE: return "Over voltage";
            case BatteryManager.BATTERY_HEALTH_UNSPECIFIED_FAILURE: return "Failure";
            case BatteryManager.BATTERY_HEALTH_COLD: return "Cold";
            default: return "Unknown";
        }
    }

    // Build a temporary EGL/GL context to query renderer/vendor/version strings.
    private void captureGpuInfo() {
        EGL10 egl = (EGL10) EGLContext.getEGL();
        EGLDisplay display = null;
        EGLContext ctx = null;
        EGLSurface surface = null;
        try {
            display = egl.eglGetDisplay(EGL10.EGL_DEFAULT_DISPLAY);
            if (display == EGL10.EGL_NO_DISPLAY) return;
            int[] ver = new int[2];
            egl.eglInitialize(display, ver);

            int[] cfgAttribs = {
                EGL10.EGL_RED_SIZE, 8, EGL10.EGL_GREEN_SIZE, 8, EGL10.EGL_BLUE_SIZE, 8,
                EGL10.EGL_DEPTH_SIZE, 0, EGL10.EGL_STENCIL_SIZE, 0,
                EGL10.EGL_RENDERABLE_TYPE, 4 /* EGL_OPENGL_ES2_BIT */,
                EGL10.EGL_SURFACE_TYPE, EGL10.EGL_PBUFFER_BIT,
                EGL10.EGL_NONE
            };
            EGLConfig[] cfgs = new EGLConfig[1];
            int[] num = new int[1];
            if (!egl.eglChooseConfig(display, cfgAttribs, cfgs, 1, num) || num[0] == 0) return;

            int[] ctxAttribs = { 0x3098 /* EGL_CONTEXT_CLIENT_VERSION */, 2, EGL10.EGL_NONE };
            ctx = egl.eglCreateContext(display, cfgs[0], EGL10.EGL_NO_CONTEXT, ctxAttribs);
            if (ctx == EGL10.EGL_NO_CONTEXT) return;

            int[] surfAttribs = { EGL10.EGL_WIDTH, 1, EGL10.EGL_HEIGHT, 1, EGL10.EGL_NONE };
            surface = egl.eglCreatePbufferSurface(display, cfgs[0], surfAttribs);
            if (surface == EGL10.EGL_NO_SURFACE) return;

            egl.eglMakeCurrent(display, surface, surface, ctx);
            glRenderer = nz(GLES20.glGetString(GLES20.GL_RENDERER));
            glVendor = nz(GLES20.glGetString(GLES20.GL_VENDOR));
            glVersion = nz(GLES20.glGetString(GLES20.GL_VERSION));
            glExtensions = nz(GLES20.glGetString(GLES20.GL_EXTENSIONS));
            egl.eglMakeCurrent(display, EGL10.EGL_NO_SURFACE, EGL10.EGL_NO_SURFACE, EGL10.EGL_NO_CONTEXT);
        } catch (Throwable ignored) {
        } finally {
            try {
                if (surface != null) egl.eglDestroySurface(display, surface);
                if (ctx != null) egl.eglDestroyContext(display, ctx);
                if (display != null) egl.eglTerminate(display);
            } catch (Throwable ignored) {}
        }
    }

    private static String nz(String s) { return s == null ? "Unknown" : s; }
}
