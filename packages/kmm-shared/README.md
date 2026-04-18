# @axis/kmm-shared

Kotlin Multiplatform business logic shared between iOS and Android apps.
Handles: connector auth, memory retrieval, response parsing.

## Setup (Phase 2)

```bash
# Install Android Studio + Xcode first
./gradlew build
```

## Layout

```
src/
├── commonMain/kotlin/com/raweval/axis/   # shared Kotlin
├── iosMain/kotlin/com/raweval/axis/      # iOS-specific
└── androidMain/kotlin/com/raweval/axis/  # Android-specific
```
