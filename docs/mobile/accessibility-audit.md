# Mobile accessibility audit notes — Session 10

**Date:** 2026-04-16
**Scope:** iOS (VoiceOver) + Android (TalkBack) Phase 1 compliance check.

## iOS (VoiceOver)

### What works
- All tab bar items have SwiftUI `.accessibilityLabel` by default (Activity, Ask, History, Connections).
- Standard UIKit/SwiftUI controls (buttons, text fields) get accessibility traits automatically.
- Navigation is linear and follows the visual tab order.

### What needs work (Phase 2)
- [ ] Custom card views in ActivityView need explicit `.accessibilityElement(children: .combine)` so VoiceOver reads the whole card as one unit instead of hitting each line separately.
- [ ] The agent response output in AskView should have `.accessibilityLabel` summarizing the answer length and citation count, not just read the raw markdown.
- [ ] The "confidence score" percentage on Surface cards should include a spoken label like "confidence 85 percent" instead of just "85%".
- [ ] Dynamic Type support — verify all text uses `.font(.body)` or relative sizes so users with large text settings can read the UI.

## Android (TalkBack)

### What works
- Compose Material components ship with `contentDescription` and `semantics` by default.
- Tab navigation is correct — TalkBack reads "Activity tab, 1 of 4" etc.
- Standard buttons and text fields are accessible out of the box.

### What needs work (Phase 2)
- [ ] LazyColumn items in each screen should use `Modifier.semantics { heading() }` for section headers so TalkBack users can jump between sections.
- [ ] Agent response cards should have a custom `contentDescription` summarizing output + citations instead of reading raw text.
- [ ] Color contrast on `InkTertiary` over `Canvas` is 4.2:1 — passes AA for large text but fails for small text. Bump tertiary to `#536580` (5.1:1).
- [ ] Touch target sizes — some Badge elements are below the 48dp minimum. Wrap in `Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)`.

## Both platforms

- [ ] Test with screen curtain / screen off to verify the entire flow (login → ask → see result) is navigable without sight.
- [ ] Haptic feedback on permission grant/deny modal for confirmation.
- [ ] Reduced-motion setting should disable the pulsing dot animation on the live task tree.
