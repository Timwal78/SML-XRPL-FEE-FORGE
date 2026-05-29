package payment

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// verifyRequest is the JSON body sent to the x402 facilitator.
type verifyRequest struct {
	PaymentProof string `json:"payment_proof"`
	Network      string `json:"network"`
	Asset        string `json:"asset"`
	Amount       string `json:"amount"`
	PayTo        string `json:"payTo"`
}

// verifyResponse mirrors the x402 facilitator response schema.
type verifyResponse struct {
	Valid       bool   `json:"valid"`
	TxSignature string `json:"tx_signature"`
	Error       string `json:"error,omitempty"`
}

// httpClient is shared across all Verify calls to reuse TCP connections.
// 5-second timeout prevents slow facilitators from blocking the request goroutine.
var httpClient = &http.Client{Timeout: 5 * time.Second}

// Verify sends proof to the x402 facilitator at facilitatorURL and returns the
// canonical on-chain transaction signature on success.
//
// The facilitator is the source of truth for settlement finality on Base.
// This call is the only network round-trip in the hot path; all other logic
// is in-memory and sub-microsecond.
func Verify(facilitatorURL, proof, alphaWallet string) (string, error) {
	body := verifyRequest{
		PaymentProof: proof,
		Network:      "base",
		Asset:        "USDC",
		Amount:       "5000",
		PayTo:        alphaWallet,
	}

	buf, err := json.Marshal(body)
	if err != nil {
		return "", fmt.Errorf("marshal verify request: %w", err)
	}

	resp, err := httpClient.Post(facilitatorURL+"/verify", "application/json", bytes.NewReader(buf))
	if err != nil {
		return "", fmt.Errorf("facilitator unreachable: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if err != nil {
		return "", fmt.Errorf("read facilitator response: %w", err)
	}

	var result verifyResponse
	if err := json.Unmarshal(raw, &result); err != nil {
		return "", fmt.Errorf("parse facilitator response (status %d): %w", resp.StatusCode, err)
	}

	if !result.Valid {
		return "", fmt.Errorf("payment rejected by facilitator: %s", result.Error)
	}

	return result.TxSignature, nil
}
