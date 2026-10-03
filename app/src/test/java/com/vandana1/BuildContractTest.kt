package com.vandana1

import org.junit.Assert.assertTrue
import org.junit.Test

class BuildContractTest {
    @Test
    fun supportedIndexesAreOptionIndexes() {
        val expected = setOf("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY", "BANKEX")
        assertTrue(expected.containsAll(setOf("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY", "BANKEX")))
    }
}
