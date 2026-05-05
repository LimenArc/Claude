package com.aethermon.streamer.auth

import android.app.Activity
import android.content.Context
import com.aethermon.streamer.BuildConfig
import com.microsoft.identity.client.*
import com.microsoft.identity.client.exception.MsalException
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class AuthManager(context: Context) {

    private val scopes = arrayOf(
        "Files.Read",
        "Files.Read.All",
        "User.Read"
    )

    private var pca: ISingleAccountPublicClientApplication? = null

    // Lazily write a runtime msal_config that injects BuildConfig values so
    // the checked-in raw/msal_config.json never contains real credentials.
    private val configFile by lazy {
        val config = """
            {
              "client_id": "${BuildConfig.CLIENT_ID}",
              "authorization_user_agent": "DEFAULT",
              "redirect_uri": "${BuildConfig.REDIRECT_URI}",
              "account_mode": "SINGLE",
              "broker_redirect_uri_registered": false,
              "authorities": [
                {
                  "type": "AAD",
                  "audience": {
                    "type": "AzureADandPersonalMicrosoftAccount",
                    "tenant_id": "common"
                  }
                }
              ]
            }
        """.trimIndent()
        val file = java.io.File(context.cacheDir, "msal_config_runtime.json")
        file.writeText(config)
        file
    }

    suspend fun initialize(context: Context): Unit = suspendCancellableCoroutine { cont ->
        PublicClientApplication.createSingleAccountPublicClientApplication(
            context,
            configFile,
            object : IPublicClientApplication.ISingleAccountApplicationCreatedListener {
                override fun onCreated(application: ISingleAccountPublicClientApplication) {
                    pca = application
                    cont.resume(Unit)
                }
                override fun onError(exception: MsalException) {
                    cont.resumeWithException(exception)
                }
            }
        )
    }

    suspend fun acquireTokenSilent(): String? {
        val app = pca ?: return null
        val account = app.currentAccount?.currentAccount ?: return null
        return suspendCancellableCoroutine { cont ->
            app.acquireTokenSilentAsync(
                scopes,
                account.authority,
                object : SilentAuthenticationCallback {
                    override fun onSuccess(result: IAuthenticationResult) {
                        cont.resume(result.accessToken)
                    }
                    override fun onError(exception: MsalException) {
                        cont.resume(null)
                    }
                }
            )
        }
    }

    suspend fun acquireTokenInteractive(activity: Activity): String =
        suspendCancellableCoroutine { cont ->
            val app = pca ?: run {
                cont.resumeWithException(IllegalStateException("MSAL not initialized"))
                return@suspendCancellableCoroutine
            }
            app.signIn(
                activity,
                null,
                scopes,
                object : AuthenticationCallback {
                    override fun onSuccess(result: IAuthenticationResult) {
                        cont.resume(result.accessToken)
                    }
                    override fun onError(exception: MsalException) {
                        cont.resumeWithException(exception)
                    }
                    override fun onCancel() {
                        cont.resumeWithException(Exception("Sign-in cancelled"))
                    }
                }
            )
        }

    suspend fun getValidToken(activity: Activity): String =
        acquireTokenSilent() ?: acquireTokenInteractive(activity)

    fun signOut() {
        pca?.signOut(object : ISingleAccountPublicClientApplication.SignOutCallback {
            override fun onSignOut() {}
            override fun onError(exception: MsalException) {}
        })
    }

    fun isSignedIn(): Boolean = pca?.currentAccount?.currentAccount != null
}
