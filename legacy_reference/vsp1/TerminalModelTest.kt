package com.vsp1.trading

import org.junit.Assert.assertTrue
import org.junit.Test

class TerminalModelTest {
    @Test fun terminalHasAtLeastThirtyTabs() {
        assertTrue(TerminalTabs.items.size >= 30)
    }

    @Test fun terminalDoesNotExposeLiveOrderTab() {
        assertTrue(TerminalTabs.items.none { it.title.contains("Live Order", ignoreCase = true) })
    }
}
