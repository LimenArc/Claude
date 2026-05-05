# OneDrive Streamer

An Android app (Kotlin) that authenticates with Microsoft via MSAL and streams your OneDrive videos using Jetpack Media3 / ExoPlayer.


---

## Prerequisites

- Android Studio Hedgehog or newer
- JDK 17
- An Azure account (free tier works)

---

## Step 1 — Register the App in Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**.
2. Fill in:
   - **Name**: `OneDrive Streamer` (or anything you like)
   - **Supported account types**: *Accounts in any organizational directory and personal Microsoft accounts*
   - **Redirect URI**: leave blank for now
3. Click **Register**. Note your **Application (client) ID** — this is your `CLIENT_ID`.

### Add the redirect URI

MSAL on Android uses a URI of the form:

```
msauth://<package_name>/<base64_url_encoded_keystore_hash>
```

To get your **keystore signature hash**:

```bash
# Debug keystore (for development)
keytool -exportcert -alias androiddebugkey \
  -keystore ~/.android/debug.keystore \
  -storepass android | openssl sha1 -binary | openssl base64
```

Construct the full redirect URI:

```
msauth://com.aethermon.streamer/<PASTE_BASE64_OUTPUT_HERE>
```

Back in Azure Portal:
1. Open your app registration → **Authentication** → **Add a platform** → **Android**.
2. Enter **Package name**: `com.aethermon.streamer`
3. Enter the **Signature hash** (base64 output from above, without `msauth://...` prefix).
4. Click **Configure**. Azure will show you the complete redirect URI — copy it.

### Add API permissions

1. **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**.
2. Add:
   - `Files.Read`
   - `Files.Read.All`
   - `User.Read`
3. Click **Grant admin consent** if your tenant requires it (optional for personal accounts).

---

## Step 2 — Configure secrets.properties

Copy the sample file and fill in your values:

```bash
cp sample.secrets.properties secrets.properties
```

Edit `secrets.properties`:

```properties
CLIENT_ID=<your Application (client) ID from Azure>
REDIRECT_URI=msauth://com.aethermon.streamer/<your_base64_hash>
```

> `secrets.properties` is git-ignored. **Never commit it.**

---

## Step 3 — Build & Run

```bash
./gradlew assembleDebug
# Install on a connected device or emulator:
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or open the project in Android Studio and press **Run**.

---

## Architecture

```
app/src/main/java/com/example/onedrivestreamer/
├── auth/
│   └── AuthManager.kt          # MSAL single-account wrapper
├── data/
│   ├── VideoItem.kt            # Parcelable domain model
│   ├── GraphModels.kt          # Retrofit / Graph API response models
│   └── VideoRepository.kt      # Fetches & pages through Graph results
├── network/
│   ├── GraphApiService.kt      # Retrofit interface
│   └── RetrofitClient.kt       # OkHttp + Retrofit singleton
└── ui/
    ├── MainActivity.kt         # NavHost host activity
    ├── VideoViewModel.kt       # Shared ViewModel (auth + data)
    ├── VideoListFragment.kt    # Screen 1 — browsable video list
    ├── VideoAdapter.kt         # RecyclerView list adapter
    └── VideoPlayerFragment.kt  # Screen 2 — ExoPlayer fullscreen
```

### Key libraries

| Purpose | Library |
|---|---|
| Auth | Microsoft MSAL 4.x |
| HTTP | Retrofit 2 + OkHttp |
| Video | Jetpack Media3 / ExoPlayer 1.3 |
| Navigation | Navigation Component (Safe Args) |
| Images | Glide |

---

## CI / CD

GitHub Actions (`.github/workflows/android.yml`) runs on every push:

1. Sets up Java 17 (Temurin)
2. Creates a dummy `secrets.properties` so Gradle doesn't fail
3. Runs `./gradlew assembleDebug`
4. Uploads the APK as an artifact (retained 14 days)

---

## Foldable support

`VideoPlayerFragment` queries `WindowMetricsCalculator` at runtime. On wide/foldable displays (aspect ratio > 1.5) the player view width is clamped to maintain the video's native aspect ratio instead of stretching.