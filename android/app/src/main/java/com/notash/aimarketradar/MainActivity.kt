package com.notash.aimarketradar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class Market(
    val title: String,
    val price: String,
    val change: String,
    val subtitle: String
)

data class RadarNews(
    val level: String,
    val title: String,
    val source: String,
    val direction: String
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { RadarApp() }
    }
}

@Composable
fun RadarApp() {
    var tab by remember { mutableIntStateOf(0) }

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF5EEAD4),
            background = Color(0xFF070B16),
            surface = Color(0xFF101827)
        )
    ) {
        Scaffold(
            containerColor = Color(0xFF070B16),
            bottomBar = {
                NavigationBar(containerColor = Color(0xFF0D1422)) {
                    val items = listOf(
                        Icons.Default.Dashboard to "رادار",
                        Icons.Default.Newspaper to "اخبار",
                        Icons.Default.WaterDrop to "نهنگ",
                        Icons.Default.Settings to "تنظیمات"
                    )
                    items.forEachIndexed { i, item ->
                        NavigationBarItem(
                            selected = tab == i,
                            onClick = { tab = i },
                            icon = { Icon(item.first, null) },
                            label = { Text(item.second) }
                        )
                    }
                }
            }
        ) { padding ->
            Box(Modifier.padding(padding)) {
                when (tab) {
                    0 -> Dashboard()
                    1 -> NewsScreen()
                    2 -> WhaleScreen()
                    else -> SettingsScreen()
                }
            }
        }
    }
}

@Composable
fun Header(title: String, subtitle: String) {
    Column(Modifier.fillMaxWidth().padding(18.dp)) {
        Text(title, fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Color.LightGray, fontSize = 13.sp)
    }
}

@Composable
fun Dashboard() {
    val markets = listOf(
        Market("₿ بیت‌کوین", "$—", "—", "قیمت از API بازار"),
        Market("♦ اتریوم", "$—", "—", "قیمت از API بازار"),
        Market("💵 دلار آزاد", "— تومان", "—", "بازار آزاد ایران"),
        Market("🥇 طلای ۱۸ عیار", "— تومان", "—", "بازار آزاد ایران"),
        Market("🥈 نقره", "—", "—", "قیمت بازار")
    )
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 20.dp)
    ) {
        item {
            Header("🤖 AI MARKET RADAR", "رصد هوشمند بازار • اخبار • نهنگ‌ها • ارز و طلا")
        }
        item {
            Card(
                Modifier.padding(horizontal = 14.dp, vertical = 6.dp).fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF102B2A))
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text("● سیستم آماده است", color = Color(0xFF5EEAD4), fontWeight = FontWeight.Bold)
                    Text("داده‌ها و هشدارهای اثرگذار بازار در همین اپ نمایش داده می‌شوند.",
                        color = Color.LightGray, modifier = Modifier.padding(top = 6.dp))
                }
            }
        }
        items(markets) { m ->
            MarketCard(m)
        }
        item {
            SectionTitle("🧠 آخرین وضعیت رادار")
            RadarNews("🔴 سطح ۳", "خبرهای با اثر بالقوه بالا", "AI Market Radar", "بررسی فوری")
            RadarNews("🟠 سطح ۲", "خبرهای مهم اقتصادی و کریپتو", "AI Market Radar", "تحت نظر")
            RadarNews("🟢 سطح ۱", "اخبار قابل توجه", "AI Market Radar", "رصد")
        }
    }
}

@Composable
fun MarketCard(m: Market) {
    Card(
        Modifier.padding(horizontal = 14.dp, vertical = 5.dp).fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF101827)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Row(
            Modifier.padding(16.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(m.title, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                Text(m.subtitle, color = Color.Gray, fontSize = 12.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(m.price, fontWeight = FontWeight.Bold)
                Text(m.change, color = Color.LightGray, fontSize = 12.sp)
            }
        }
    }
}

@Composable
fun SectionTitle(text: String) {
    Text(text, fontSize = 19.sp, fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(18.dp, 22.dp, 18.dp, 8.dp))
}

@Composable
fun RadarNews(level: String, title: String, source: String, direction: String) {
    Card(
        Modifier.padding(horizontal = 14.dp, vertical = 5.dp).fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF101827))
    ) {
        Column(Modifier.padding(15.dp)) {
            Text(level, fontWeight = FontWeight.Bold)
            Text(title, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(top = 5.dp))
            Text("$source • $direction", color = Color.Gray, fontSize = 12.sp,
                modifier = Modifier.padding(top = 5.dp))
        }
    }
}

@Composable
fun NewsScreen() {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 20.dp)) {
        item { Header("📰 اخبار هوشمند", "غربالگری و تحلیل فارسی اخبار بازار") }
        item {
            InfoCard(
                "فیلتر خبر",
                "خبرهای مهم اقتصادی، فارکس و کریپتو بر اساس امتیاز اهمیت جدا می‌شوند."
            )
        }
        item {
            InfoCard(
                "تحلیل AI",
                "برای خبرهای مهم، اثر احتمالی روی BTC، دلار، طلا، نفت و سهام تحلیل می‌شود."
            )
        }
        item {
            InfoCard(
                "هشدار",
                "جهت بازار احتمالی است و سیگنال قطعی خرید یا فروش صادر نمی‌شود."
            )
        }
    }
}

@Composable
fun WhaleScreen() {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 20.dp)) {
        item { Header("🐋 WHALE ALERT", "رهگیری انتقال‌های سنگین رمزارزی") }
        item {
            InfoCard(
                "سطح ۱",
                "حرکت سنگین — حداقل ارزش قابل تنظیم."
            )
        }
        item {
            InfoCard(
                "سطح ۲",
                "حرکت بسیار سنگین — انتقال‌های بزرگ برای بررسی فوری."
            )
        }
        item {
            InfoCard(
                "تحلیل",
                "انتقال بزرگ به‌تنهایی به معنی خرید یا فروش قطعی نیست."
            )
        }
    }
}

@Composable
fun SettingsScreen() {
    var notifications by remember { mutableStateOf(true) }
    var telegram by remember { mutableStateOf(true) }

    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 20.dp)) {
        item { Header("⚙️ تنظیمات", "کنترل اعلان‌ها و اتصال سرویس‌ها") }
        item {
            SettingRow("🔔 اعلان‌های بازار", notifications) { notifications = it }
        }
        item {
            SettingRow("📣 ارسال Telegram", telegram) { telegram = it }
        }
        item {
            InfoCard(
                "اتصال به موتور اصلی",
                "این اپ برای داده زنده باید به API/Backend پروژه AI Market Radar متصل شود. کلیدهای API داخل APK قرار داده نمی‌شوند."
            )
        }
        item {
            InfoCard(
                "بازار آزاد ایران",
                "دلار، یورو، درهم، پوند، لیر، یوان و طلای ۱۸ عیار برای نمایش نرخ آزاد در طراحی اپ پیش‌بینی شده‌اند."
            )
        }
    }
}

@Composable
fun SettingRow(title: String, checked: Boolean, onChecked: (Boolean) -> Unit) {
    Card(
        Modifier.padding(horizontal = 14.dp, vertical = 5.dp).fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF101827))
    ) {
        Row(
            Modifier.padding(12.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(title)
            Switch(checked = checked, onCheckedChange = onChecked)
        }
    }
}

@Composable
fun InfoCard(title: String, body: String) {
    Card(
        Modifier.padding(horizontal = 14.dp, vertical = 6.dp).fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF101827))
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, fontWeight = FontWeight.Bold, fontSize = 17.sp)
            Text(body, color = Color.LightGray, modifier = Modifier.padding(top = 7.dp))
        }
    }
}
