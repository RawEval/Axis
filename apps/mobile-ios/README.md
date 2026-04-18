# Axis iOS

Swift + SwiftUI. Minimum iOS 16. Phase 2 deliverable.

## Setup

```bash
# Requires Xcode 15+
open Axis.xcodeproj
```

Generate the Xcode project with `xcodegen` (recommended) or create a new one pointing at
`Axis/` as sources. Shared business logic lives in `packages/kmm-shared`.

## Structure

```
Axis/
├── AxisApp.swift         # @main
├── ContentView.swift     # Tab-based root
├── Views/                # Feed, Chat, Connections, History, Memory, Settings
├── Models/               # SwiftUI observable view models
└── Services/             # API client, WebSocket, notifications
```
