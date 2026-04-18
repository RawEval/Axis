package com.raweval.axis.auth

import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

/**
 * Phase 1 biometric gate — wraps AndroidX BiometricPrompt.
 *
 * Call `showPrompt` when the activity resumes from background while a
 * JWT is cached. Falls through silently when biometrics are unavailable
 * (emulator, no enrolled fingerprints) so dev isn't blocked.
 */
object BiometricGate {

    fun canAuthenticate(activity: FragmentActivity): Boolean {
        val mgr = BiometricManager.from(activity)
        return mgr.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG) ==
            BiometricManager.BIOMETRIC_SUCCESS
    }

    fun showPrompt(
        activity: FragmentActivity,
        onSuccess: () -> Unit,
        onFailure: () -> Unit,
    ) {
        val executor = ContextCompat.getMainExecutor(activity)
        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                onSuccess()
            }
            override fun onAuthenticationFailed() {
                onFailure()
            }
            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                if (errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON ||
                    errorCode == BiometricPrompt.ERROR_USER_CANCELED) {
                    onFailure()
                } else {
                    // Hardware unavailable, no biometrics enrolled, etc. → pass through.
                    onSuccess()
                }
            }
        }
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Unlock Axis")
            .setSubtitle("Authenticate to continue")
            .setNegativeButtonText("Cancel")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .build()

        BiometricPrompt(activity, executor, callback).authenticate(info)
    }
}
