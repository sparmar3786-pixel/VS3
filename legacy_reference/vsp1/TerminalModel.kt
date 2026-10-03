package com.vsp1.trading

data class TerminalTab(val title: String, val icon: String)

object TerminalTabs {
    val items = listOf(
        TerminalTab("Dashboard","⌂"), TerminalTab("Market","◉"), TerminalTab("Watchlist","★"),
        TerminalTab("Option Chain","▤"), TerminalTab("OI Analysis","OI"), TerminalTab("Greeks","Δ"),
        TerminalTab("IV Surface","IV"), TerminalTab("PCR","P"), TerminalTab("Max Pain","M"),
        TerminalTab("Support / Resistance","↕"), TerminalTab("Charts","⌁"), TerminalTab("Multi-Timeframe","TF"),
        TerminalTab("Trade Plans","TP"), TerminalTab("Signals","⚡"), TerminalTab("6-Layer AI","AI"),
        TerminalTab("Data Guard","L1"), TerminalTab("Regime","L2"), TerminalTab("Ensemble","L3"),
        TerminalTab("Online ML","L4"), TerminalTab("Risk Guard","L5"), TerminalTab("Supervisor","L6"),
        TerminalTab("Strategies","Σ"), TerminalTab("Backtest","BT"), TerminalTab("Paper Portfolio","PF"),
        TerminalTab("Positions","POS"), TerminalTab("Paper Orders","ORD"), TerminalTab("P&L","₹"),
        TerminalTab("Alerts","!"), TerminalTab("Scanner","⌕"), TerminalTab("News","N"),
        TerminalTab("Journal","J"), TerminalTab("CSV Upload","⇧"), TerminalTab("Broker Status","B"),
        TerminalTab("API Status","API"), TerminalTab("Settings","⚙"), TerminalTab("Theme","◐"),
        TerminalTab("Help","?")
    )
}
