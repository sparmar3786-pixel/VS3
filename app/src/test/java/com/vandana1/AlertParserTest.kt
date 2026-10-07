package com.vandana1

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertParserTest {
    private val body = """
        {"seq": 7, "events": [
          {"seq": 6, "kind": "ENTRY", "title": "ENTRY NIFTY CALL 24000CE", "body": "Entry 100"},
          {"seq": 7, "kind": "AI", "title": "AI CALL BUY NIFTY", "body": "all models agree"}
        ]}
    """.trimIndent()

    @Test
    fun parsesSequenceAndEvents() {
        val batch = AlertParser.parse(body)
        assertNotNull(batch)
        assertEquals(7L, batch!!.seq)
        assertEquals(2, batch.events.size)
        assertEquals("AI", batch.events[1].kind)
        assertEquals("AI CALL BUY NIFTY", batch.events[1].title)
    }

    @Test
    fun badJsonIsNullInsteadOfCrashing() {
        assertNull(AlertParser.parse("<html>502 Bad Gateway</html>"))
        assertNull(AlertParser.parse(""))
    }

    @Test
    fun eventsMissingFromResponseGiveEmptyBatch() {
        val batch = AlertParser.parse("""{"seq": 3}""")
        assertEquals(3L, batch!!.seq)
        assertTrue(batch.events.isEmpty())
    }

    @Test
    fun firstPollOnlyLearnsTheSequence() {
        val batch = AlertParser.parse(body)!!
        assertTrue(AlertParser.fresh(batch, null).isEmpty())
    }

    @Test
    fun onlyEventsNewerThanTheLastSeenSequenceAreShown() {
        val batch = AlertParser.parse(body)!!
        assertEquals(listOf(7L), AlertParser.fresh(batch, 6L).map { it.seq })
        assertTrue(AlertParser.fresh(batch, 7L).isEmpty())
    }

    @Test
    fun serverRestartResyncsWithoutReplaying() {
        val restarted = AlertParser.parse("""{"seq": 1, "events": [{"seq": 1, "title": "old"}]}""")!!
        assertTrue(AlertParser.fresh(restarted, 40L).isEmpty())
    }
}
