package com.raweval.axis.ui

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * Axis design tokens — mirror the Tailwind palette from apps/web.
 * See docs/mobile/design.md.
 */
object AxisColors {
    // Light
    val Canvas       = Color(0xFFF7F8FA)
    val Raised       = Color(0xFFFFFFFF)
    val Subtle       = Color(0xFFEEF1F6)
    val Ink          = Color(0xFF0F172A)
    val InkSecondary = Color(0xFF475569)
    val InkTertiary  = Color(0xFF64748B)
    val Edge         = Color(0xFFE2E8F0)
    val Brand        = Color(0xFF2563EB)
    val Success      = Color(0xFF16A34A)
    val Warning      = Color(0xFFD97706)
    val Danger       = Color(0xFFDC2626)

    // Dark
    val CanvasDark       = Color(0xFF111119)
    val RaisedDark       = Color(0xFF1E1E28)
    val InkDark          = Color(0xFFEEF0F3)
    val EdgeDark         = Color(0xFF333641)
    val SubtleDark       = Color(0xFF262630)
    val InkSecondaryDark = Color(0xFFADB5C4)
}

object AxisRadius {
    val Card = 10.dp
    val Chip = 6.dp
}

object AxisSpacing {
    val Tight = 8.dp
    val Base = 12.dp
    val Loose = 16.dp
    val Section = 24.dp
}
