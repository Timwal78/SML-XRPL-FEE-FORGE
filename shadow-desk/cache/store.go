// Package cache provides a thread-safe, in-memory store for real-time alpha signals.
// Backed by sync.Map: reads are lock-free, writes are O(1) amortized.
package cache

import (
	"sync"
	"time"
)

// AlphaSignal is the latest Pine Script signal ingested for a given ticker.
type AlphaSignal struct {
	Ticker     string   `json:"ticker"`
	SignalType string   `json:"signal_type"`
	Price      float64  `json:"price"`
	Timestamp  time.Time `json:"timestamp"`
	// Extended institutional fields — populated by future data sources.
	// nil means the field has not been set for this signal.
	GammaWall *float64 `json:"gamma_wall"`
	BlockFlow *float64 `json:"block_flow"`
}

// Store is the shared in-memory cache. One instance per process.
type Store struct {
	m sync.Map
}

// Default is the process-wide alpha cache used by all handlers.
var Default = &Store{}

// Set upserts the latest signal for ticker, stamping it with the current UTC time.
func (s *Store) Set(sig AlphaSignal) {
	sig.Timestamp = time.Now().UTC()
	s.m.Store(sig.Ticker, sig)
}

// Get returns the latest signal for ticker.
// The second return value is false when no signal has been ingested yet.
func (s *Store) Get(ticker string) (AlphaSignal, bool) {
	v, ok := s.m.Load(ticker)
	if !ok {
		return AlphaSignal{}, false
	}
	return v.(AlphaSignal), true
}
