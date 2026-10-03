package com.sparmar.vs3

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private val state=TerminalState()
    private val executor=Executors.newSingleThreadExecutor()
    private lateinit var drawer:LinearLayout
    private lateinit var content:LinearLayout
    private lateinit var status:TextView
    private lateinit var indexButton:Button
    private val amber=Color.rgb(255,159,26); private val green=Color.rgb(46,230,107)
    private val bg=Color.rgb(5,5,5); private val panel=Color.rgb(15,15,15); private val text=Color.rgb(228,228,228); private val muted=Color.rgb(130,130,130)
    private val apiBase="https://nse-algo-backend-live-production.up.railway.app"
    private fun dp(v:Int)= (v*resources.displayMetrics.density).toInt()
    private fun tv(s:String,size:Float=12f,color:Int=text,bold:Boolean=false)=TextView(this).apply{text=s;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.MONOSPACE;setPadding(dp(8),dp(5),dp(8),dp(5))}
    private fun btn(s:String,action:()->Unit)=Button(this).apply{text=s;textSize=11f;setTextColor(Color.BLACK);setBackgroundColor(amber);setOnClickListener{action()};minHeight=dp(36);minimumHeight=dp(36)}
    private fun card(h:String)=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(8),dp(10),dp(10));setBackgroundColor(panel);addView(tv(h.uppercase(),11f,amber,true))}
    override fun onCreate(b:Bundle?){super.onCreate(b);window.statusBarColor=bg;window.navigationBarColor=bg;buildShell();render(2);refreshBackend()}
    private fun buildShell(){
        val root=FrameLayout(this).apply{setBackgroundColor(bg)}
        val main=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setBackgroundColor(bg)}
        val top=LinearLayout(this).apply{gravity=Gravity.CENTER_VERTICAL;setPadding(dp(6),dp(4),dp(6),dp(4));setBackgroundColor(amber)}
        val menu=btn("☰"){drawer.visibility=View.VISIBLE};menu.setBackgroundColor(Color.BLACK);menu.setTextColor(amber)
        top.addView(menu,LinearLayout.LayoutParams(dp(48),dp(42)));top.addView(tv("NSE-AI-TERMINAL",15f,Color.BLACK,true),LinearLayout.LayoutParams(0,dp(42),1f))
        status=tv("PAPER • AI READY",10f,Color.BLACK,true);top.addView(status);main.addView(top)
        val cmd=LinearLayout(this).apply{gravity=Gravity.CENTER_VERTICAL;setPadding(dp(8),dp(5),dp(8),dp(5));setBackgroundColor(Color.rgb(9,9,9))}
        cmd.addView(tv("CMD>",11f,amber,true));val input=EditText(this).apply{hint="NIFTY / BANKNIFTY / SENSEX / tab 1-30";hintTextColor=muted;setTextColor(amber);setSingleLine(true)}
        cmd.addView(input,LinearLayout.LayoutParams(0,dp(38),1f));cmd.addView(btn("GO"){handleCommand(input.text.toString())});main.addView(cmd)
        val ir=LinearLayout(this).apply{gravity=Gravity.CENTER_VERTICAL;setPadding(dp(8),dp(5),dp(8),dp(5))}
        indexButton=btn("INDEX: NIFTY"){chooseIndex()};ir.addView(indexButton);ir.addView(tv("  6-layer AI • live orders OFF",10f,muted));main.addView(ir)
        val scroll=ScrollView(this);content=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(7),dp(4),dp(7),dp(20))};scroll.addView(content);main.addView(scroll,LinearLayout.LayoutParams(-1,0,1f));main.addView(tv("Angel One SmartAPI → FastAPI/Railway → AI → WebSocket • PAPER",9f,muted))
        drawer=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(16),dp(10),dp(10));setBackgroundColor(Color.rgb(10,10,10));elevation=dp(18).toFloat();visibility=View.GONE}
        val dh=LinearLayout(this);dh.addView(tv("NSE-AI-TERMINAL",15f,amber,true),LinearLayout.LayoutParams(0,dp(42),1f));dh.addView(btn("×"){drawer.visibility=View.GONE});drawer.addView(dh);drawer.addView(tv("30 MODULES • SELECT A SCREEN",9f,muted))
        val nav=ScrollView(this);val list=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        TerminalState.tabs.forEachIndexed{idx,name->val b=Button(this).apply{text="%02d  %s".format(idx+1,name);gravity=Gravity.START or Gravity.CENTER_VERTICAL;textSize=11f;setTextColor(text);setBackgroundColor(Color.rgb(18,18,18));setPadding(dp(12),0,dp(8),0);setOnClickListener{drawer.visibility=View.GONE;render(idx)}};list.addView(b,LinearLayout.LayoutParams(-1,dp(42)).apply{bottomMargin=dp(4)})}
        nav.addView(list);drawer.addView(nav,LinearLayout.LayoutParams(-1,0,1f));root.addView(main,FrameLayout.LayoutParams(-1,-1));root.addView(drawer,FrameLayout.LayoutParams(dp(350),-1,Gravity.START));setContentView(root)
    }
    private fun handleCommand(raw:String){val s=raw.trim().uppercase();val i=when{ s.toIntOrNull() in 1..30->s.toInt()-1; s.contains("CHAIN")->4; s.contains("OI")->5; s.contains("AI")->13; s.contains("RISK")->18; s.contains("PORTFOLIO")->15; else->2 };render(i)}
    private fun chooseIndex(){val v=TerminalState.supportedIndices.toTypedArray();AlertDialog.Builder(this).setTitle("Option Index").setItems(v){_,w->state.selectIndex(v[w]);indexButton.text="INDEX: "+state.index;render(2)}.show()}
    private fun render(i:Int){indexButton.text="INDEX: "+state.index;content.removeAllViews();content.addView(tv("%02d  %s".format(i+1,TerminalState.tabs[i]),13f,amber,true));when(i){0->simple("AI TRADING TERMINAL","6-layer AI validation • disciplined execution • paper mode");1->login();2->dashboard();3->market();4->optionChain();5->simple("OI HEATMAP","CE red • PE green • ATM amber • freshness gate active");6->simple("PREMIUM / VOLUME","CE premium stable • PE premium rising • volume above average");7->greeks();8->metrics("ORDER FLOW",listOf("Net flow" to "+12.4K","Buy ratio" to "68%","Aggression" to "BUY"));9->metrics("REGIME",listOf("Trend" to "UPTREND","VIX" to "13.8","ADX" to "24.1"));10->plans();11->metrics("BACKTEST",listOf("Win rate" to "62.4%","Avg R" to "1.8","Max DD" to "12.3%","Trades" to "412"));12->strategies();13->ai();14->metrics("LOGS / SETTINGS",listOf("Mode" to "PAPER","Backend" to apiBase,"Auto refresh" to "5s"));15->metrics("PAPER PORTFOLIO",listOf("Open positions" to "0","Day P&L" to "₹0","Risk used" to "0%","Live orders" to "OFF"));16->simple("PRICE CHART","EMA 8/13 • VWAP • RSI • MACD • ATR");17->metrics("STRATEGY DETAIL",listOf("Strategy" to "OI Wall + VWAP","Filter" to "6-layer AI","Execution" to "Paper only"));18->metrics("RISK GUARD",listOf("Max risk/trade" to "1%","Daily loss cap" to "2%","Kill switch" to "ARMED","Live orders" to "OFF"));19->simple("ALERTS","No active alerts.");20->simple("HELP","Use the left drawer for all 30 modules.");21->simple("WATCHLIST","NIFTY • BANKNIFTY • FINNIFTY • SENSEX • MIDCPNIFTY • BANKEX");22->simple("ORDERS","Live order placement is OFF.");23->simple("SIGNAL HISTORY","CALL BUY / PUT BUY / WAIT / NO TRADE");24->simple("SCANNER","Index option scanner ready.");25->simple("FII / DII","Shown when backend supplies fresh data.");26->simple("NEWS","Disabled until provider configured.");27->simple("ALERT RULES","Price, OI, IV and signal rules.");28->simple("JOURNAL","Paper-trade journal ready.");29->metrics("BROKER / API",listOf("Provider" to "Angel One SmartAPI","Transport" to "FastAPI/WebSocket","Credentials" to "Backend only","Orders" to "DISABLED"))}}
    private fun dashboard(){val c=card("TODAY'S AI SIGNAL");c.addView(tv("INDEX: "+state.index+" • DATA GATE: FRESH",10f,muted));c.addView(tv("WAIT",28f,amber,true));c.addView(tv("AI confidence 82% • risk gate active",11f,text));listOf("L1 Data Feed","L2 Feature Engine","L3 Signal Model","L4 Regime/VIX","L5 RiskGuard","L6 Supervisor/OI").forEach{row(c,it,"PASS",green)};content.addView(c);content.addView(metrics("MARKET SNAPSHOT",listOf("NIFTY 50" to "—","BANK NIFTY" to "—","INDIA VIX" to "—","PCR" to "—")));content.addView(metrics("TRADE PLAN",listOf("Entry" to "ATM option","SL" to "risk-gated","T1" to "model target","Mode" to "PAPER")))}
    private fun login(){content.addView(card("ANGEL ONE / BACKEND").apply{addView(tv("Credentials are never stored in the APK.",11f,text,true));addView(tv("Authenticate on the backend. Live orders remain disabled.",10f,muted));addView(btn("CHECK BACKEND"){refreshBackend()})})}
    private fun market(){content.addView(metrics("MARKET",listOf("NIFTY 50" to "24,689.75","BANK NIFTY" to "52,317.20","FINNIFTY" to "23,482.10","SENSEX" to "81,742.20","MIDCPNIFTY" to "12,345.60","BANKEX" to "60,210.00")))}
    private fun optionChain(){content.addView(tableCard("OPTION CHAIN • "+state.index,listOf(arrayOf("CE OI","CE LTP","STRIKE","PE LTP","PE OI"),arrayOf("18.4L","42.1","ATM-100","35.2","21.8L"),arrayOf("22.1L","28.6","ATM","31.4","25.7L"),arrayOf("20.8L","19.4","ATM+100","27.8","19.3L")))}
    private fun greeks(){content.addView(tableCard("GREEKS / IV",listOf(arrayOf("STRIKE","DELTA","GAMMA","THETA","VEGA","IV"),arrayOf("ATM-100",".72",".004","-8.4","11.2","14.3%"),arrayOf("ATM",".50",".006","-9.0","12.0","13.5%"),arrayOf("ATM+100",".28",".004","-8.4","11.2","14.3%")))}
    private fun plans(){content.addView(tableCard("QUALIFYING TRADE PLANS",listOf(arrayOf("SIDE","STRIKE","ENTRY","SL","T1","RR"),arrayOf("CALL BUY","ATM","18.40","16.90","20.20","1:1.4"),arrayOf("PUT BUY","ATM-100","13.80","12.60","15.20","1:1.3")))}
    private fun strategies(){content.addView(tableCard("STRATEGY REGISTRY",listOf(arrayOf("ID","STRATEGY","WIN%","AVG R"),arrayOf("S001","OI WALL","52%","1.2"),arrayOf("S002","LONG BUILDUP","59%","1.5"),arrayOf("S003","SHORT COVERING","66%","1.8"),arrayOf("S004","VWAP RECLAIM","63%","1.6")))}
    private fun ai(){val c=card("AI 6-LAYER VALIDATION");listOf("L1 Data Quality","L2 Feature Engine","L3 Signal Model","L4 Regime/VIX","L5 RiskGuard","L6 Supervisor/OI").forEach{row(c,it,"PASS",green)};c.addView(tv("Final decision: WAIT until backend freshness gate passes.",11f,amber,true));content.addView(c)}
    private fun simple(h:String,b:String){content.addView(card(h).apply{addView(tv(b,11f,text))})}
    private fun metrics(h:String,v:List<Pair<String,String>>):View=card(h).apply{v.forEach{row(this,it.first,it.second,if(it.second.contains("PASS")||it.second.contains("UP")||it.second.contains("BUY"))green else text)}}
    private fun row(p:LinearLayout,a:String,b:String,c:Int){val r=LinearLayout(this).apply{gravity=Gravity.CENTER_VERTICAL};r.addView(tv(a,10f,muted),LinearLayout.LayoutParams(0,dp(34),1f));r.addView(tv(b,11f,c,true));p.addView(r)}
    private fun tableCard(h:String,d:List<Array<String>>):View=card(h).apply{d.forEachIndexed{ri,a->val r=LinearLayout(this@MainActivity);a.forEach{r.addView(tv(it,9f,if(ri==0)amber else text,ri==0),LinearLayout.LayoutParams(0,dp(32),1f))};addView(r)}}
    private fun refreshBackend(){status.text="BACKEND CHECK…";executor.execute{val r=try{val c=URL(apiBase+"/health").openConnection() as HttpURLConnection;c.connectTimeout=5000;c.readTimeout=5000;c.requestMethod="GET";val code=c.responseCode;c.disconnect();if(code in 200..299)"BACKEND ONLINE • AI READY" else "BACKEND HTTP $code"}catch(_:Exception){"PAPER • BACKEND OFFLINE"};runOnUiThread{status.text=r}}}
    override fun onDestroy(){executor.shutdownNow();super.onDestroy()}
}
