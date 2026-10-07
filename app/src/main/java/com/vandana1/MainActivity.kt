package com.vandana1

import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private var client: ApiClient? = null
    private var running = false
    private val ui = Handler(Looper.getMainLooper())
    @Volatile private var lastSeq: Long? = null
    @Volatile private var polling = false
    private var loopStarted = false

    private val tick = object : Runnable {
        override fun run() {
            pollAlerts()
            if (running) refresh()
            ui.postDelayed(this, 5000)
        }
    }

    private lateinit var status: TextView
    private lateinit var spot: TextView
    private lateinit var chain: TextView
    private lateinit var index: Spinner
    private val indexes = listOf("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY", "BANKEX")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createAlertChannel()
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 1)
        }
        showConnect()
    }

    private fun baseLayout(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(20, 18, 20, 18)
        setBackgroundColor(Color.rgb(11, 18, 32))
    }

    private fun tv(text: String, size: Float = 15f): TextView = TextView(this).apply {
        this.text = text
        textSize = size
        setTextColor(Color.WHITE)
        setPadding(0, 7, 0, 7)
    }

    private fun button(text: String, action: () -> Unit) = Button(this).apply {
        this.text = text
        setOnClickListener { action() }
    }

    private fun field(hint: String, numeric: Boolean = false) = EditText(this).apply {
        this.hint = hint
        setTextColor(Color.WHITE)
        setHintTextColor(Color.LTGRAY)
        if (numeric) inputType = InputType.TYPE_CLASS_NUMBER
        layoutParams = LinearLayout.LayoutParams(-1, -2)
    }

    private fun showConnect() {
        val root = baseLayout()
        root.addView(tv("VANDANA1 • NATIVE KOTLIN", 22f))
        root.addView(tv("Live NSE / Angel One terminal", 14f))
        val url = field("Railway backend URL")
        url.setText("https://nse-algo-backend-live-production.up.railway.app")
        val clientId = field("Angel One Client ID")
        val pin = field("MPIN", true).apply {
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
        }
        val totp = field("Current 6-digit TOTP", true)
        val apiKey = field("SmartAPI key (optional if server configured)")
        val token = field("Terminal token (optional)")
        listOf(url, clientId, pin, totp, apiKey, token).forEach { root.addView(it) }
        val msg = tv("Credentials are entered at runtime; none are embedded in the APK.")
        root.addView(msg)
        root.addView(button("CONNECT") {
            val base = url.text.toString().trim()
            if (base.isBlank()) {
                msg.text = "Backend URL is required."
                return@button
            }
            client = ApiClient(base, token.text.toString())
            msg.text = "Checking backend..."
            io.execute {
                val h = client!!.health()
                runOnUiThread {
                    if (h.code in 200..299) {
                        if (clientId.text.isBlank()) {
                            msg.text = "Backend reachable. Angel login can be completed when credentials are entered."
                            showDashboard()
                        } else {
                            msg.text = "Backend reachable. Connecting Angel One..."
                            io.execute {
                                val r = client!!.login(clientId.text.toString(), pin.text.toString(), totp.text.toString(), apiKey.text.toString())
                                runOnUiThread {
                                    if (r.code in 200..299) showDashboard()
                                    else msg.text = "Angel login failed (" + r.code + "): " + safe(r.body)
                                }
                            }
                        }
                    } else {
                        msg.text = "Backend failed (" + h.code + "): " + safe(h.body)
                    }
                }
            }
        })
        setContentView(root)
    }

    private fun showDashboard() {
        running = true
        if (!loopStarted) {
            loopStarted = true
            ui.postDelayed(tick, 5000)
        }
        val root = baseLayout()
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        header.addView(tv("VANDANA1", 22f), LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(button("REFRESH") { refresh() })
        root.addView(header)
        status = tv("LIVE • checking...", 13f)
        spot = tv("Spot: —", 28f)
        chain = tv("Option chain: —", 13f)
        index = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, indexes)
            setSelection(0)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    if (running) refresh()
                }
            }
        }
        root.addView(status)
        root.addView(tv("INDEX"))
        root.addView(index)
        root.addView(spot)
        val scroll = ScrollView(this).apply { addView(chain) }
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(button("PAUSE AUTO REFRESH") { running = !running })
        setContentView(root)
        refresh()
    }

    private fun refresh() {
        if (!running) return
        val c = client ?: return
        val selected = indexes.getOrElse(index.selectedItemPosition) { "NIFTY" }
        io.execute {
            val m = c.market()
            val o = c.optionChain(selected)
            runOnUiThread {
                if (m.code in 200..299) {
                    try {
                        val j = JSONObject(m.body)
                        val ltp = if (j.isNull("ltp")) "—" else j.optString("ltp", "—")
                        spot.text = "Spot: " + ltp
                        status.text = if (j.optBoolean("connected", true))
                            "LIVE • Angel One"
                        else
                            "BACKEND • Angel disconnected — log in again"
                    } catch (e: Exception) {
                        status.text = "MARKET ERROR: unreadable response"
                    }
                } else {
                    status.text = "MARKET ERROR " + m.code + (if (m.code == 0) " " + safe(m.body) else "")
                }
                chain.text = if (o.code in 200..299) formatChain(o.body)
                else "OPTION CHAIN ERROR " + o.code + "\n" + safe(o.body)
            }
        }
    }

    private fun formatChain(body: String): String {
        val j = try { JSONObject(body) } catch (e: Exception) { return "Unreadable option chain response" }
        val rows = j.optJSONArray("rows") ?: return body
        val out = StringBuilder("STRIKE        TYPE     LTP       OI\n")
        for (i in 0 until minOf(rows.length(), 40)) {
            val r = rows.optJSONObject(i) ?: continue
            out.append(String.format("%-12s %-8s %-9s %s\n",
                r.optString("strike", "—"),
                r.optString("type", "—"),
                r.optString("ltp", "—"),
                r.optString("oi", "—")))
        }
        return out.toString()
    }

    private fun safe(body: String): String = body.replace(Regex("[\\r\\n]+"), " ").take(180)

    private fun createAlertChannel() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(
            NotificationChannel(ALERT_CHANNEL, "Signal alerts", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "ENTRY / EXIT signals and AI verdicts"
                enableVibration(true)
            }
        )
    }

    private fun pollAlerts() {
        val c = client ?: return
        if (polling || io.isShutdown) return
        polling = true
        try {
            io.execute {
                try {
                    val r = c.alerts(lastSeq)
                    if (r.code in 200..299) {
                        val batch = AlertParser.parse(r.body)
                        if (batch != null) {
                            val fresh = AlertParser.fresh(batch, lastSeq)
                            lastSeq = batch.seq
                            if (fresh.isNotEmpty()) runOnUiThread { fresh.forEach { showAlert(it) } }
                        }
                    }
                } finally {
                    polling = false
                }
            }
        } catch (e: Exception) {
            polling = false
        }
    }

    private fun showAlert(a: AlertEvent) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val open = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val n = Notification.Builder(this, ALERT_CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(a.title)
            .setContentText(a.body)
            .setStyle(Notification.BigTextStyle().bigText(a.body))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        nm.notify(a.seq.toInt(), n)
    }

    override fun onResume() { super.onResume(); if (client != null) running = true }
    override fun onPause() { running = false; super.onPause() }
    override fun onDestroy() {
        running = false
        ui.removeCallbacksAndMessages(null)
        io.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val ALERT_CHANNEL = "vs3_signal_alerts"
    }
}
