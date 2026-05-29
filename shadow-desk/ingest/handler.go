// Package ingest handles the TradingView Pine Script alert webhook.
package ingest

import (
	"crypto/subtle"
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/cache"
)

// Payload is the JSON body expected from a TradingView Pine Script alert.
// The secret_key field must match INGEST_SECRET on the server.
type Payload struct {
	Ticker     string  `json:"ticker"`
	SignalType string  `json:"signal_type"`
	Price      float64 `json:"price"`
	SecretKey  string  `json:"secret_key"`
}

// Handler returns an HTTP handler for POST /v1/ingest.
//
// On success the signal is stored in the shared cache and returned as JSON.
// The handler uses constant-time comparison for the secret key to prevent
// timing-based key-enumeration attacks from external callers.
func Handler(ingestSecret string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method_not_allowed"})
			return
		}

		var p Payload
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid_json"})
			return
		}

		// Constant-time comparison prevents an attacker from inferring the secret
		// length or prefix by measuring response latency.
		if ingestSecret != "" {
			if subtle.ConstantTimeCompare([]byte(p.SecretKey), []byte(ingestSecret)) != 1 {
				slog.Warn("ingest auth failed", "ticker", p.Ticker, "remote", r.RemoteAddr)
				writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
				return
			}
		}

		if p.Ticker == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "ticker_required"})
			return
		}

		sig := cache.AlphaSignal{
			Ticker:     p.Ticker,
			SignalType: p.SignalType,
			Price:      p.Price,
		}
		cache.Default.Set(sig)

		slog.Info("signal ingested", "ticker", p.Ticker, "signal_type", p.SignalType, "price", p.Price)

		// Return the stored signal (with its server-stamped timestamp) so the
		// caller can confirm exactly what was saved.
		stored, _ := cache.Default.Get(p.Ticker)
		writeJSON(w, http.StatusOK, stored)
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
