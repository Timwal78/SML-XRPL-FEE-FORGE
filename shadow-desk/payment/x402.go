// Package payment implements the x402 payment lifecycle:
// challenge generation, proof extraction, and facilitator-based verification.
package payment

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
)

// PaymentRequired is the structured body encoded into the X-PAYMENT-REQUIRED
// header on every HTTP 402 response. It follows the x402 open standard
// (https://x402.org/spec) and is parseable by any autonomous AI agent with
// a CDP/Agentic Wallet to self-fund the request without human intervention.
type PaymentRequired struct {
	Version        string `json:"version"`
	Scheme         string `json:"scheme"`
	Network        string `json:"network"`
	Asset          string `json:"asset"`
	// USDC contract on Base mainnet — verified on Basescan.
	Contract       string `json:"contract"`
	// Amount in USDC's smallest unit (6 decimals).
	// 5000 micro-USDC == 0.005 USDC per request.
	Amount         string `json:"amount"`
	Decimals       int    `json:"decimals"`
	// PayTo is the alpha provider's on-chain address receiving 99% of each payment.
	PayTo          string `json:"payTo"`
	Memo           string `json:"memo"`
	FacilitatorURL string `json:"facilitatorUrl"`
}

// Challenge writes an HTTP 402 response with the x402 payment challenge.
// The X-PAYMENT-REQUIRED header carries a Base64-encoded JSON payment spec
// that autonomous AI agents decode to learn the cost, wallet, and network.
func Challenge(w http.ResponseWriter, alphaWallet, facilitatorURL string) {
	req := PaymentRequired{
		Version:        "x402/1.0",
		Scheme:         "exact",
		Network:        "base",
		Asset:          "USDC",
		Contract:       "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
		Amount:         "5000",
		Decimals:       6,
		PayTo:          alphaWallet,
		Memo:           "shadow-desk-alpha-v1",
		FacilitatorURL: facilitatorURL,
	}

	payload, err := json.Marshal(req)
	if err != nil {
		http.Error(w, `{"error":"internal_error"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-PAYMENT-REQUIRED", base64.StdEncoding.EncodeToString(payload))
	w.WriteHeader(http.StatusPaymentRequired)

	// Human-readable body for debugging — autonomous agents use the header.
	json.NewEncoder(w).Encode(map[string]interface{}{
		"error":   "payment_required",
		"message": "Decode X-PAYMENT-REQUIRED header (base64 JSON), send USDC on Base, then retry with X-PAYMENT-SIGNATURE.",
		"payment": req,
	})
}

// ExtractProof pulls the raw payment proof from the request.
// Supports two header styles:
//   - X-PAYMENT-SIGNATURE: <proof>  (x402 spec)
//   - Authorization: x402 <proof>   (Coinbase CDP agent style)
//
// Returns the proof string and true when found, empty string and false otherwise.
func ExtractProof(r *http.Request) (string, bool) {
	if sig := r.Header.Get("X-Payment-Signature"); sig != "" {
		return sig, true
	}
	auth := r.Header.Get("Authorization")
	if len(auth) > 5 && auth[:5] == "x402 " {
		return auth[5:], true
	}
	return "", false
}
