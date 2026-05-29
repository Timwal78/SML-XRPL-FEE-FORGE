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

// MarkIfUnseen atomically checks whether sig has been seen and, if not, marks
// it as spent in a single critical section. Returns true if the signature was
// fresh (caller may proceed), false if it was already present (replay attack).
//
// This replaces the previous IsSeen+Mark two-step, which had a TOCTOU race:
// two goroutines could both pass IsSeen before either called Mark, allowing
// the same transaction to redeem two alpha responses.
func (g *Guard) MarkIfUnseen(sig string) bool {
	g.mu.Lock()
	defer g.mu.Unlock()

	if _, exists := g.seen[sig]; exists {
		return false
	}

	g.seen[sig] = entry{seenAt: time.Now()}
	g.prune()
	return true
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
