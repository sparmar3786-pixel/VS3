package com.sparmar.vs3

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TerminalStateTest {
    @Test fun indexSelectionKeepsSupportedOptionIndicesOnly() {
        val state = TerminalState()
        state.selectIndex("BANKNIFTY")
        assertEquals("BANKNIFTY", state.index)
        state.selectIndex("RELIANCE")
        assertEquals("BANKNIFTY", state.index)
    }

    @Test fun tradeSignalIsOneOfSafeTerminalStates() {
        val signal = TerminalState().signal
        assertTrue(signal in setOf("CALL BUY", "PUT BUY", "WAIT", "NO TRADE"))
    }

    @Test fun sidebarHasExactlyThirtyTabs() {
        assertEquals(30, TerminalState.tabs.size)
    }
}
