// Package mcp serves the Model Context Protocol auto-discovery manifest.
// Enterprise AI agents (Coinbase CDP, OpenAI Assistants, Agentic.market crawlers)
// fetch /.well-known/mcp.json to discover available tools, their parameters,
// and x402 payment requirements before making any API calls.
package mcp

import (
	"encoding/json"
	"net/http"
)

// manifest is the static MCP schema describing The Shadow Desk's capabilities.
// It is serialised once at startup and served verbatim on every request.
var manifest = map[string]any{
	"schema_version": "mcp/1.0",
	"name":           "shadow-desk",
	"description":    "Institutional trading alpha — real-time Pine Script signals, gamma walls, and block flows. Pay-per-request via x402/USDC on Base. Zero signups, zero API keys.",
	"tools": []map[string]any{
		{
			"name": "get_institutional_trading_alpha",
			"description": "Returns real-time institutional alpha for a given ticker: latest Pine Script signal type, price, gamma wall levels, and block flow imbalances. " +
				"Calling this function triggers an x402 micropayment wall. " +
				"Autonomous agents should: (1) call the endpoint, (2) decode the X-PAYMENT-REQUIRED header (base64 JSON), " +
				"(3) send the specified USDC amount on Base to the payTo address, " +
				"(4) retry with the on-chain tx signature in X-Payment-Signature.",
			"parameters": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"ticker": map[string]any{
						"type":        "string",
						"description": "Equity or crypto ticker symbol (e.g. AMC, NVDA, BTC, ETH)",
					},
				},
				"required": []string{"ticker"},
			},
			"x402": map[string]any{
				"required":          true,
				"network":           "base",
				"asset":             "USDC",
				"contract":          "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
				"price_per_call":    "0.005",
				"price_unit":        "USDC",
				"payment_endpoint":  "/v1/alpha/stream",
				"proof_header":      "X-Payment-Signature",
				"fallback_header":   "Authorization: x402 <proof>",
				"facilitator":       "https://x402.org/facilitator",
			},
		},
	},
}

// payload is serialised once at package init to avoid repeated marshalling.
var payload []byte

func init() {
	var err error
	payload, err = json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		// manifest is a static literal — this can only fail due to a programmer error.
		panic("mcp: failed to marshal static manifest: " + err.Error())
	}
}

// Handler serves GET /.well-known/mcp.json.
// The response is pre-serialised at startup so this handler is allocation-free.
func Handler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(payload)
	}
}
