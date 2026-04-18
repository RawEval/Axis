import LocalAuthentication

/// Phase 1 biometric gate — prompts FaceID/TouchID on app foreground
/// when a JWT exists. Falls through silently if biometrics are unavailable
/// (e.g. simulator) so dev isn't blocked.
///
/// Usage: call `BiometricAuth.authenticate()` in the app delegate / scene
///        phase change when transitioning from background → active.
enum BiometricAuth {
    static func authenticate(reason: String = "Unlock Axis") async -> Bool {
        let context = LAContext()
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            // Biometrics not available — fall through (don't block the user)
            return true
        }
        do {
            return try await context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: reason
            )
        } catch {
            return false
        }
    }
}
