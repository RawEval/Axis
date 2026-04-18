package com.raweval.axis.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.raweval.axis.ui.AxisColors
import com.raweval.axis.ui.AxisSpacing

@Composable
fun AskScreen() {
    var prompt by remember { mutableStateOf("") }

    Column(
        modifier = Modifier.fillMaxSize().padding(AxisSpacing.Loose),
        verticalArrangement = Arrangement.spacedBy(AxisSpacing.Base),
    ) {
        Text(
            text = "Ask Axis",
            color = AxisColors.Ink,
        )
        Text(
            text = "Describe what you want done across your connected tools.",
            color = AxisColors.InkTertiary,
        )
        OutlinedTextField(
            value = prompt,
            onValueChange = { prompt = it },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("What do you need?") },
        )
    }
}
