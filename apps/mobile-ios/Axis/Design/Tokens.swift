import SwiftUI

/// Axis design tokens — mirror the Tailwind palette from apps/web.
/// See docs/mobile/design.md.
enum AxisColors {
    // Light mode
    static let canvas       = Color(red: 0.969, green: 0.973, blue: 0.980)   // #F7F8FA
    static let raised       = Color.white                                    // #FFFFFF
    static let subtle       = Color(red: 0.933, green: 0.945, blue: 0.965)   // #EEF1F6
    static let ink          = Color(red: 0.059, green: 0.090, blue: 0.165)   // #0F172A
    static let inkSecondary = Color(red: 0.278, green: 0.333, blue: 0.412)   // #475569
    static let inkTertiary  = Color(red: 0.392, green: 0.455, blue: 0.545)   // #64748B
    static let edge         = Color(red: 0.886, green: 0.910, blue: 0.941)   // #E2E8F0
    static let brand        = Color(red: 0.149, green: 0.388, blue: 0.922)   // #2563EB
    static let success      = Color(red: 0.086, green: 0.639, blue: 0.290)   // #16A34A
    static let warning      = Color(red: 0.851, green: 0.467, blue: 0.024)   // #D97706
    static let danger       = Color(red: 0.863, green: 0.149, blue: 0.149)   // #DC2626

    // Dark mode — adaptive colors for SwiftUI
    static let canvasDark       = Color(red: 0.067, green: 0.067, blue: 0.098)   // #111119
    static let raisedDark       = Color(red: 0.118, green: 0.118, blue: 0.157)   // #1E1E28
    static let inkDark          = Color(red: 0.933, green: 0.941, blue: 0.953)   // #EEF0F3
    static let edgeDark         = Color(red: 0.200, green: 0.212, blue: 0.255)   // #333641

    // Adaptive helper — auto-switches on colorScheme
    static func adaptive(light: Color, dark: Color) -> Color {
        // SwiftUI Color doesn't have a built-in adaptive init, but
        // wrapping in .init(UIColor { ... }) does the trick.
        Color(uiColor: UIColor { traitCollection in
            traitCollection.userInterfaceStyle == .dark
                ? UIColor(dark) : UIColor(light)
        })
    }
}

enum AxisRadius {
    static let card: CGFloat = 10
    static let chip: CGFloat = 6
}

enum AxisSpacing {
    static let tight: CGFloat = 8
    static let base: CGFloat = 12
    static let loose: CGFloat = 16
    static let section: CGFloat = 24
}
