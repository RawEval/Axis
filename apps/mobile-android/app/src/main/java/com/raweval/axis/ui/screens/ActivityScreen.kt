package com.raweval.axis.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.raweval.axis.ui.AxisColors
import com.raweval.axis.ui.AxisSpacing

@Composable
fun ActivityScreen() {
    Box(
        modifier = Modifier.fillMaxSize().padding(AxisSpacing.Loose),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = "No signals yet. Connect tools on the web to start receiving proactive surfaces.",
            color = AxisColors.InkTertiary,
        )
    }
}
