package com.aethermon.streamer.auth // Ensure this matches your package name

import android.content.Context
import com.microsoft.identity.client.*
import com.microsoft.identity.client.exception.MsalException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.InputStream

class AuthManager(private val context: Context) {

    private var msalApp: ISingleAccountPublicClientApplication? = null

    // Initialize MSAL - This usually happens in a background thread or async
    suspend fun init(configStream: InputStream) = withContext(Dispatchers.IO) {
        msalApp = PublicClientApplication.createSingleAccountPublicClientApplication(
            context,
            configStream
        )
    }

    /**
     * This is the "One-line fix." 
     * We move the call to a background thread (IO) to prevent the crash.
     */
    suspend fun getCurrentAccount(): IAccount? = withContext(Dispatchers.IO) {
        return@withContext msalApp?.currentAccount?.account
    }

    /**
     * Checks if a user is signed in without crashing the Main Thread.
     */
    suspend fun isSignedIn(): Boolean = withContext(Dispatchers.IO) {
        return@withContext msalApp?.currentAccount?.account != null
    }

    // Sign in logic
    fun signIn(activity: android.app.Activity, callback: AuthenticationCallback) {
        msalApp?.signIn(activity, null, arrayOf("Files.Read.All"), callback)
    }

    // Sign out logic
    suspend fun signOut(): Boolean = withContext(Dispatchers.IO) {
        return@withContext try {
            msalApp?.signOut() ?: false
            true
        } catch (e: Exception) {
            false
        }
    }
}
