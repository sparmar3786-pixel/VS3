package com.vandana1

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class ApiResult(val code: Int, val body: String)

class ApiClient(private val baseUrl: String, private val appToken: String?) {
    private fun request(path: String, method: String = "GET", body: String? = null): ApiResult {
        val url = URL(baseUrl.trimEnd('/') + path)
        val c = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8000
            readTimeout = 12000
            setRequestProperty("Accept", "application/json")
            appToken?.trim()?.takeIf { it.isNotEmpty() }?.let { setRequestProperty("X-App-Key", it) }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                outputStream.use { it.write(body.toByteArray()) }
            }
        }
        return try {
            ApiResult(c.responseCode, (if (c.responseCode in 200..299) c.inputStream else c.errorStream)
                ?.bufferedReader()?.use { it.readText() }.orEmpty())
        } finally { c.disconnect() }
    }

    fun health() = request("/health")
    fun login(clientId: String, pin: String, totp: String, apiKey: String) =
        request("/v1/angel/login", "POST", JSONObject().apply {
            put("clientId", clientId)
            put("pin", pin)
            put("totp", totp)
            if (apiKey.isNotBlank()) put("apiKey", apiKey)
        }.toString())
    fun market() = request("/v1/angel/market")
    fun optionChain(index: String) = request("/v1/angel/option-chain?symbol=" + index + "&count=40")
}
