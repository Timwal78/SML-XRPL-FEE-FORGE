// Package replay prevents double-spending of x402 payment signatures.
// Every verified transaction signature is recorded here; duplicate submissions
// are rejected before the alpha payload is served.
package replay

import (
	"sync"
	"time"
)

const retentionWindow = 24 * time.Hour // exceeds Base network finality by orders of magnitude

type entry struct {
	seenAt time.Time
}

// Guard is a bounded, in-memory set of seen payment signatures.
// Entries older than retentionWindow are pruned on every write to cap memory usage.
type Guard struct {
	mu   sync.Mutex
	seen map[string]entry
}

// Default is the process-wide replay guard shared by all handlers.
var Default = &Guard{seen: make(map[string]entry)}

// IsSeen returns true if sig has been submitted before.
// Called before Mark to give the caller a chance to reject before side-effects.
func (g *Guard) IsSeen(sig string) bool {
	g.mu.Lock()
	defer g.mu.Unlock()
	_, exists := g.seen[sig]
	return exists
}

// Mark records sig as spent. Must only be called after successful facilitator
// verification to avoid poisoning the guard with invalid signatures.
func (g *Guard) Mark(sig string) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.seen[sig] = entry{seenAt: time.Now()}
	g.prune()
}

// prune removes entries older than retentionWindow.
// Callers must hold g.mu. O(n) but infrequent in practice; Base settlement
// signatures are typically unique and the 24-hour window keeps the map small.
func (g *Guard) prune() {
	cutoff := time.Now().Add(-retentionWindow)
	for k, e := range g.seen {
		if e.seenAt.Before(cutoff) {
			delete(g.seen, k)
		}
	}
}
