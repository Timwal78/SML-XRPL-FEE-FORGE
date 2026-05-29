// Package alpha implements the x402-gated institutional data delivery endpoint.
package alpha

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"time"

	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/billing"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/cache"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/config"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/payment"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/replay"
)

// priceUSDC is the cost per request in USDC decimal form.
// 0.005 USDC == 5000 in the 6-decimal USDC smallest unit.
const priceUSDC = 0.005

// Response is the JSON payload delivered to a client after successful x402 settlement.
type Response struct {
	Ticker     string    `json:"ticker"`
	SignalType string    `json:"signal_type"`
	Price      float64   `json:"price"`
	Timestamp  time.Time `json:"timestamp"`
	// Optional fields populated when richer institutional data is available.
	GammaWall *float64  `json:"gamma_wall"`
	BlockFlow *float64  `json:"block_flow"`
	ServedAt  time.Time `json:"served_at"`
}

// Handler returns an HTTP handler for GET /v1/alpha/stream.
//
// x402 lifecycle:
//  1. No payment proof in headers  → emit HTTP 402 challenge.
//  2. Proof present                → verify with facilitator.
//  3. Replay guard (atomic)        → reject already-spent signatures.
//  4. Log billing event            → serve alpha payload.
func Handler(cfg *config.Config) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method_not_allowed"})
			return
		}

		ticker := r.URL.Query().Get("ticker")
		if ticker == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "ticker_required"})
			return
		}

		// Step 1 — Extract payment proof.
		// Autonomous AI agents attach proof via X-Payment-Signature or Authorization: x402 <proof>.
		proof, ok := payment.ExtractProof(r)
		if !ok {
			// No proof present: send 402 challenge so the agent can fund and retry.
			slog.Info("payment required", "ticker", ticker, "remote", r.RemoteAddr)
			payment.Challenge(w, r, cfg.AlphaProviderWallet, cfg.FacilitatorURL)
			return
		}

		// Step 2 — Verify settlement finality via the x402 facilitator.
		txSig, err := payment.Verify(cfg.FacilitatorURL, proof, cfg.AlphaProviderWallet)
		if err != nil {
			slog.Warn("payment verification failed", "ticker", ticker, "err", err)
			writeJSON(w, http.StatusPaymentRequired, map[string]string{
				"error":   "payment_verification_failed",
				"message": err.Error(),
			})
			return
		}

		// Step 3 — Atomic replay guard.
		// MarkIfUnseen checks-and-sets in one critical section, eliminating the
		// TOCTOU race that would exist with a separate IsSeen + Mark pair.
		if !replay.Default.MarkIfUnseen(txSig) {
			slog.Warn("replay attack detected", "tx_sig", txSig, "ticker", ticker)
			writeJSON(w, http.StatusConflict, map[string]string{
				"error":   "replay_detected",
				"message": "This transaction has already been redeemed.",
			})
			return
		}

		// Step 4 — Record billing event and serve alpha payload.
		billing.Default.Record(txSig, cfg.AlphaProviderWallet, cfg.PlatformWallet, ticker, priceUSDC)

		sig, found := cache.Default.Get(ticker)
		if !found {
			// Payment accepted but no signal ingested yet; return an empty payload.
			// The client paid and gets a valid (but empty) response — this is intentional.
			writeJSON(w, http.StatusOK, Response{
				Ticker:   ticker,
				ServedAt: time.Now().UTC(),
			})
			return
		}

		writeJSON(w, http.StatusOK, Response{
			Ticker:     sig.Ticker,
			SignalType: sig.SignalType,
			Price:      sig.Price,
			Timestamp:  sig.Timestamp,
			GammaWall:  sig.GammaWall,
			BlockFlow:  sig.BlockFlow,
			ServedAt:   time.Now().UTC(),
		})
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
