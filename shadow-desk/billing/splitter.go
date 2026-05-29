// Package billing records every settled x402 micropayment and computes the
// transparent revenue split: 99% to the alpha provider, 1% to the platform.
package billing

import (
	"log/slog"
	"sync"
	"time"
)

const (
	AlphaShare    = 0.99 // alpha signal provider's cut
	PlatformShare = 0.01 // protocol fee retained by the platform
)

// Event records one settled x402 micropayment and its computed revenue split.
type Event struct {
	TxSignature    string    `json:"tx_signature"`
	AmountUSDC     float64   `json:"amount_usdc"`
	AlphaWallet    string    `json:"alpha_wallet"`
	PlatformWallet string    `json:"platform_wallet"`
	AlphaCut       float64   `json:"alpha_cut"`
	PlatformCut    float64   `json:"platform_cut"`
	Ticker         string    `json:"ticker"`
	SettledAt      time.Time `json:"settled_at"`
}

// Ledger is an append-only, in-memory billing log.
// A read-write mutex allows many concurrent reads (admin dashboard)
// while serialising writes (one per settled payment).
type Ledger struct {
	mu     sync.RWMutex
	events []Event
}

// Default is the process-wide billing ledger.
var Default = &Ledger{}

// Record appends a new billing event and emits it as structured JSON via slog.
// amountUSDC should be expressed as a decimal (e.g. 0.005 for 0.005 USDC).
func (l *Ledger) Record(txSig, alphaWallet, platformWallet, ticker string, amountUSDC float64) {
	e := Event{
		TxSignature:    txSig,
		AmountUSDC:     amountUSDC,
		AlphaWallet:    alphaWallet,
		PlatformWallet: platformWallet,
		AlphaCut:       amountUSDC * AlphaShare,
		PlatformCut:    amountUSDC * PlatformShare,
		Ticker:         ticker,
		SettledAt:      time.Now().UTC(),
	}

	l.mu.Lock()
	l.events = append(l.events, e)
	l.mu.Unlock()

	slog.Info("x402 settled",
		"tx_sig", txSig,
		"ticker", ticker,
		"amount_usdc", amountUSDC,
		"alpha_cut", e.AlphaCut,
		"platform_cut", e.PlatformCut,
		"alpha_wallet", alphaWallet,
		"platform_wallet", platformWallet,
	)
}

// All returns a snapshot of the entire ledger. Safe to call concurrently.
func (l *Ledger) All() []Event {
	l.mu.RLock()
	defer l.mu.RUnlock()
	result := make([]Event, len(l.events))
	copy(result, l.events)
	return result
}
