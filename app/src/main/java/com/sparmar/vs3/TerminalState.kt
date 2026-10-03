package com.sparmar.vs3

class TerminalState {
    companion object {
        val supportedIndices = setOf("NIFTY","BANKNIFTY","FINNIFTY","SENSEX","MIDCPNIFTY","BANKEX")
        val tabs = listOf("Splash","Login","Dashboard","Market","Option Chain","OI Heatmap","Premium/Vol","Greeks/IV","Order Flow","Regime","Trade Plans","Backtest","Strategies","AI 6-Layer","Logs/Settings","Portfolio","Charts","Strategy Detail","Risk","Alerts","Help","Watchlist","Orders","Signal History","Scanner","FII/DII","News","Alert Rules","Journal","Broker/API")
    }
    var index = "NIFTY"; private set
    var signal = "WAIT"; private set
    fun selectIndex(value:String){ if(value in supportedIndices) index=value }
    fun setSignal(value:String){ if(value in setOf("CALL BUY","PUT BUY","WAIT","NO TRADE")) signal=value }
}
