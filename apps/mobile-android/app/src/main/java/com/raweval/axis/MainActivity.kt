package com.raweval.axis

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.raweval.axis.ui.AxisColors
import com.raweval.axis.ui.screens.ActivityScreen
import com.raweval.axis.ui.screens.AskScreen
import com.raweval.axis.ui.screens.ConnectionsScreen
import com.raweval.axis.ui.screens.HistoryScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AxisTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = AxisColors.Canvas) {
                    AxisRoot()
                }
            }
        }
    }
}

@Composable
fun AxisTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = AxisColors.Brand,
            onPrimary = AxisColors.Raised,
            background = AxisColors.Canvas,
            surface = AxisColors.Raised,
            onBackground = AxisColors.Ink,
            onSurface = AxisColors.Ink,
        ),
        content = content,
    )
}

private enum class Tab { Activity, Ask, History, Connections }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AxisRoot() {
    var tab by remember { mutableStateOf(Tab.Activity) }

    Scaffold(
        containerColor = AxisColors.Canvas,
        bottomBar = {
            NavigationBar(containerColor = AxisColors.Raised) {
                NavigationBarItem(
                    selected = tab == Tab.Activity,
                    onClick = { tab = Tab.Activity },
                    icon = { Icon(Icons.Filled.List, contentDescription = "Activity") },
                    label = { Text("Activity") },
                )
                NavigationBarItem(
                    selected = tab == Tab.Ask,
                    onClick = { tab = Tab.Ask },
                    icon = { Icon(Icons.Filled.Send, contentDescription = "Ask") },
                    label = { Text("Ask") },
                )
                NavigationBarItem(
                    selected = tab == Tab.History,
                    onClick = { tab = Tab.History },
                    icon = { Icon(Icons.Filled.DateRange, contentDescription = "History") },
                    label = { Text("History") },
                )
                NavigationBarItem(
                    selected = tab == Tab.Connections,
                    onClick = { tab = Tab.Connections },
                    icon = { Icon(Icons.Filled.Build, contentDescription = "Tools") },
                    label = { Text("Tools") },
                )
            }
        },
    ) { padding ->
        Surface(
            modifier = Modifier.fillMaxSize().padding(padding),
            color = AxisColors.Canvas,
        ) {
            when (tab) {
                Tab.Activity -> ActivityScreen()
                Tab.Ask -> AskScreen()
                Tab.History -> HistoryScreen()
                Tab.Connections -> ConnectionsScreen()
            }
        }
    }
}
