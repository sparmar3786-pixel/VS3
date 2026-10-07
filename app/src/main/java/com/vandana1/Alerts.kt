package com.vandana1

import org.json.JSONObject

data class AlertEvent(val seq: Long, val kind: String, val title: String, val body: String)
data class AlertBatch(val seq: Long, val events: List<AlertEvent>)

object AlertParser {
    fun parse(body: String): AlertBatch? = try {
        val root = JSONObject(body)
        val arr = root.optJSONArray("events")
        val out = ArrayList<AlertEvent>()
        if (arr != null) {
            for (i in 0 until arr.length()) {
                val e = arr.optJSONObject(i) ?: continue
                out.add(AlertEvent(
                    e.optLong("seq"),
                    e.optString("kind", "INFO"),
                    e.optString("title"),
                    e.optString("body")
                ))
            }
        }
        AlertBatch(root.optLong("seq", 0L), out)
    } catch (e: Exception) {
        null
    }

    fun fresh(batch: AlertBatch, lastSeq: Long?): List<AlertEvent> =
        if (lastSeq == null || batch.seq < lastSeq) emptyList()
        else batch.events.filter { it.seq > lastSeq }
}
