# TradingView Alert Setup — SML Leviathan Matrix

## Step 1: Add the Pine Script
1. Open TradingView → Pine Editor (bottom bar)
2. Paste the contents of `SML_Leviathan_Matrix.pine`
3. Click **Save** then **Add to chart**

## Step 2: Create Alerts (do for each: LONG, SHORT, SQUEEZE)
1. Right-click any signal arrow on chart → **Add Alert**
   OR press `Alt+A`
2. **Condition**: Select `SML Leviathan Matrix Alerts` → `SML LONG Signal`
3. **Alert actions**: Check ✅ **Webhook URL**
4. **Webhook URL**: `https://shadow-desk.onrender.com/v1/ingest`
5. **Message** (paste exactly):
```json
{"ticker":"{{ticker}}","action":"EXECUTE_LONG","close":"{{close}}","volume":"{{volume}}","system":"SML_Leviathan","timeframe":"{{interval}}","secret_key":"sml-ingest-3e25f14cae28c8382940b0aa8f27d51283388802"}
```
6. Click **Create**

Repeat for SHORT and SQUEEZE conditions.

## Step 3: Add second webhook (Signal API → Discord broadcast)
Add ANOTHER alert for the same conditions, webhook URL:
`https://sml-x402-signal-api.onrender.com/api/tv/equities/webhook`
Header: `x-webhook-secret: test_secret`

Message:
```json
{"ticker":"{{ticker}}","action":"{{strategy.order.action}}","close":"{{close}}","system":"SML_Leviathan"}
```

## Verification
After setting up alerts:
1. Wait for a signal on any chart
2. Check Render logs at: https://dashboard.render.com/web/srv-d8curaojs32c73au9ku0/logs
3. Check Discord — you should see the broadcast

## Symbols to add to chart for testing
GME, AMC, IWM, TSLA, PLUG, SPCE, BBBY, MVIS, KOSS, NAKD
