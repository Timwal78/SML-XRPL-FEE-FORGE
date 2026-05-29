// Package payment implements the x402 v2 payment lifecycle.
// Spec: https://docs.cdp.coinbase.com/x402/docs/x402-http-spec
package payment

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
)

// ── x402 v2 types ────────────────────────────────────────────────────────────

// Resource describes the protected resource. Required at top-level in v2.
type Resource struct {
	URL         string `json:"url"`
	Description string `json:"description"`
	MimeType    string `json:"mimeType"`
}

// AcceptEntry is one accepted payment option in the top-level accepts[] array.
type AcceptEntry struct {
	Scheme string `json:"scheme"`
	Network string `json:"network"`
	// Asset is the ERC-20 contract address on the target network.
	Asset string `json:"asset"`
	// Amount is the v2 field for price (v1 used maxAmountRequired — now invalid).
	Amount            string `json:"amount"`
	Resource          string `json:"resource"`
	Description       string `json:"description"`
	MimeType          string `json:"mimeType"`
	PayTo             string `json:"payTo"`
	MaxTimeoutSeconds int    `json:"maxTimeoutSeconds"`
	Extra             Extra  `json:"extra"`
}

// Extra carries asset display metadata (name, decimals).
type Extra struct {
	Name     string `json:"name"`
	Decimals int    `json:"decimals"`
}

// BazaarInfo is the discovery metadata block required by Coinbase Bazaar / Agentic.market.
// The validator requires this to be nested under bazaar.info, not at bazaar top-level.
type BazaarInfo struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Category    string   `json:"category"`
	Keywords    []string `json:"keywords"`
}

// BazaarExtension is the full Coinbase Bazaar discovery extension.
// Structure: { info: {...}, schema: {...} }
type BazaarExtension struct {
	Info   BazaarInfo     `json:"info"`
	// Schema is a JSON Schema (draft-07) that describes the API output structure.
	// Bazaar validators use this during indexing to confirm response shape.
	Schema map[string]any `json:"schema"`
}

// Extensions carries optional protocol extensions keyed by name.
type Extensions struct {
	Bazaar BazaarExtension `json:"bazaar"`
}

// PaymentRequired is the full x402 v2 top-level response object.
// It is base64-encoded and delivered via the PAYMENT-REQUIRED response header.
type PaymentRequired struct {
	X402Version int           `json:"x402Version"`
	Resource    Resource      `json:"resource"`
	Accepts     []AcceptEntry `json:"accepts"`
	Extensions  Extensions    `json:"extensions"`
}

// ── Constants ─────────────────────────────────────────────────────────────────

const (
	// USDC contract on Base mainnet — verified on Basescan.
	usdcContractBase = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

	// 5000 micro-USDC == 0.005 USDC per request (6 decimal places).
	priceAmount = "5000"

	// 5-minute settlement window.
	maxTimeoutSeconds = 300
)

// alphaOutputSchema is the JSON Schema (draft-07) describing the /v1/alpha/stream
// response payload. Bazaar uses this for structural validation during indexing.
var alphaOutputSchema = map[string]any{
	"$schema": "http://json-schema.org/draft-07/schema#",
	"type":    "object",
	"properties": map[string]any{
		"ticker":      map[string]any{"type": "string", "description": "Equity or crypto ticker symbol"},
		"signal_type": map[string]any{"type": "string", "description": "Pine Script signal identifier (e.g. Ignition_Locked)"},
		"price":       map[string]any{"type": "number", "description": "Asset price at signal trigger"},
		"timestamp":   map[string]any{"type": "string", "format": "date-time", "description": "Signal ingest timestamp (UTC)"},
		"gamma_wall":  map[string]any{"type": []any{"number", "null"}, "description": "Options gamma wall strike level"},
		"block_flow":  map[string]any{"type": []any{"number", "null"}, "description": "Dark pool block flow imbalance"},
		"served_at":   map[string]any{"type": "string", "format": "date-time", "description": "Response serve timestamp (UTC)"},
	},
	"required": []string{"ticker", "served_at"},
}

// ── Public API ────────────────────────────────────────────────────────────────

// Challenge writes an HTTP 402 response with a fully spec-compliant x402 v2
// payment challenge. The PAYMENT-REQUIRED header carries a base64-encoded JSON
// payload that autonomous AI agents decode to learn the cost, wallet, and network.
func Challenge(w http.ResponseWriter, r *http.Request, alphaWallet, facilitatorURL string) {
	// Build the resource URL from the incoming request so the resource field
	// always reflects the exact URL the agent tried to access.
	resourceURL := "https://shadow-desk.onrender.com" + r.URL.Path
	if r.URL.RawQuery != "" {
		resourceURL += "?" + r.URL.RawQuery
	}

	description := "Real-time US equity squeeze alpha signal. $0.005 USDC per call on Base mainnet."

	req := PaymentRequired{
		X402Version: 2,
		Resource: Resource{
			URL:         resourceURL,
			Description: description,
			MimeType:    "application/json",
		},
		Accepts: []AcceptEntry{
			{
				Scheme:  "exact",
				Network: "base",
				Asset:   usdcContractBase,
				// Amount is the v2 field name — maxAmountRequired was the v1 name.
				Amount:            priceAmount,
				Resource:          resourceURL,
				Description:       description,
				MimeType:          "application/json",
				PayTo:             alphaWallet,
				MaxTimeoutSeconds: maxTimeoutSeconds,
				Extra: Extra{
					Name:     "USD Coin",
					Decimals: 6,
				},
			},
		},
		Extensions: Extensions{
			Bazaar: BazaarExtension{
				// info is the nested block the Bazaar validator requires for discovery.
				Info: BazaarInfo{
					Name:        "Shadow Desk Alpha Stream",
					Description: "Institutional US equity short-squeeze alpha for autonomous AI agents. Real-time Pine Script signals, gamma walls, and block flows. Pay-per-request via x402 micropayments.",
					Category:    "finance",
					Keywords:    []string{"short-squeeze", "GME", "AMC", "IWM", "alpha", "equity", "meme-stock", "USDC", "x402"},
				},
				Schema: alphaOutputSchema,
			},
		},
	}

	payload, err := json.Marshal(req)
	if err != nil {
		http.Error(w, `{"error":"internal_error"}`, http.StatusInternalServerError)
		return
	}

	encoded := base64.StdEncoding.EncodeToString(payload)

	w.Header().Set("Content-Type", "application/json")
	// x402 v2 spec: header is PAYMENT-REQUIRED (no X- prefix).
	w.Header().Set("PAYMENT-REQUIRED", encoded)
	// Keep X-PAYMENT-REQUIRED for backward compat with v1 agents.
	w.Header().Set("X-PAYMENT-REQUIRED", encoded)
	w.WriteHeader(http.StatusPaymentRequired)

	// Human-readable body — agents use the header.
	json.NewEncoder(w).Encode(map[string]any{
		"error":       "payment_required",
		"x402Version": 2,
		"message":     "Send USDC on Base then retry with X-Payment-Signature header.",
		"payment":     req,
	})
}

// ExtractProof pulls the raw payment proof from the request.
// Supports three header styles per x402 v1+v2:
//   - X-Payment-Signature: <proof>      (x402 v1)
//   - X-PAYMENT-SIGNATURE: <proof>      (x402 v1 alt)
//   - Authorization: x402 <proof>       (Coinbase CDP agent style)
func ExtractProof(r *http.Request) (string, bool) {
	if sig := r.Header.Get("X-Payment-Signature"); sig != "" {
		return sig, true
	}
	if sig := r.Header.Get("X-PAYMENT-SIGNATURE"); sig != "" {
		return sig, true
	}
	auth := r.Header.Get("Authorization")
	if len(auth) > 5 && auth[:5] == "x402 " {
		return auth[5:], true
	}
	return "", false
}
