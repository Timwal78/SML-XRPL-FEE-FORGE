package stream

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/pkg/models"
)

type client struct {
	ch   chan []byte
	done chan struct{}
}

// Hub manages SSE clients and aggregates payment statistics via Redis.
type Hub struct {
	mu        sync.RWMutex
	clients   map[*client]struct{}
	broadcast chan []byte
	rdb       *redis.Client
}

func NewHub(rdb *redis.Client) *Hub {
	return &Hub{
		clients:   make(map[*client]struct{}),
		broadcast: make(chan []byte, 256),
		rdb:       rdb,
	}
}

func (h *Hub) Run() {
	for msg := range h.broadcast {
		h.mu.RLock()
		for c := range h.clients {
			select {
			case c.ch <- msg:
			default:
				// slow client — drop event rather than block
			}
		}
		h.mu.RUnlock()
	}
}

func (h *Hub) Publish(event interface{}) {
	b, err := json.Marshal(event)
	if err != nil {
		log.Error().Err(err).Msg("hub: marshal failed")
		return
	}
	select {
	case h.broadcast <- b:
	default:
		log.Warn().Msg("hub: broadcast channel full, dropping event")
	}
}

func (h *Hub) ServeSSE(w http.ResponseWriter, r *http.Request) {
	fl, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unsupported", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	c := &client{ch: make(chan []byte, 64), done: make(chan struct{})}
	h.mu.Lock()
	h.clients[c] = struct{}{}
	h.mu.Unlock()
	defer func() {
		h.mu.Lock()
		delete(h.clients, c)
		h.mu.Unlock()
		close(c.done)
	}()

	// Send snapshot on connect
	snap := h.buildSnapshot(r.Context())
	if b, err := json.Marshal(map[string]interface{}{"type": "snapshot", "data": snap}); err == nil {
		fmt.Fprintf(w, "data: %s\n\n", b)
		fl.Flush()
	}

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case msg := <-c.ch:
			fmt.Fprintf(w, "data: %s\n\n", msg)
			fl.Flush()
		case <-ticker.C:
			fmt.Fprintf(w, ": heartbeat\n\n")
			fl.Flush()
		case <-r.Context().Done():
			return
		}
	}
}

func (h *Hub) HandleStats(w http.ResponseWriter, r *http.Request) {
	snap := h.buildSnapshot(r.Context())
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	json.NewEncoder(w).Encode(snap)
}

// RecordPayment persists payment metrics in Redis.
func (h *Hub) RecordPayment(ctx context.Context, payer, amountDropsStr string) {
	amountDrops := parseDrops(amountDropsStr)
	pipe := h.rdb.Pipeline()
	nowMs := float64(time.Now().UnixMilli())
	pipe.Incr(ctx, "x402:total_tx")
	pipe.IncrByFloat(ctx, "x402:total_usdc_drops", amountDrops)
	pipe.ZAdd(ctx, "x402:tx_window", redis.Z{Score: nowMs, Member: fmt.Sprintf("%d", time.Now().UnixNano())})
	pipe.ZRemRangeByScore(ctx, "x402:tx_window", "0",
		fmt.Sprintf("%d", time.Now().Add(-time.Hour).UnixMilli()))
	pipe.HIncrBy(ctx, "x402:agent:"+payer, "requests", 1)
	pipe.HIncrByFloat(ctx, "x402:agent:"+payer, "usdc_drops", amountDrops)
	pipe.HSet(ctx, "x402:agent:"+payer, "last_seen", time.Now().Unix())
	pipe.SAdd(ctx, "x402:agents", payer)
	_, _ = pipe.Exec(ctx)
}

// IncrAgentReputation increments the XRPL-backed reputation score for a payer.
func (h *Hub) IncrAgentReputation(ctx context.Context, payer string) {
	h.rdb.HIncrBy(ctx, "x402:agent:"+payer, "reputation", 1)
}

func (h *Hub) buildSnapshot(ctx context.Context) models.StatsSnapshot {
	totalDrops, _ := h.rdb.Get(ctx, "x402:total_usdc_drops").Float64()
	totalTx, _ := h.rdb.Get(ctx, "x402:total_tx").Int64()
	txWindow, _ := h.rdb.ZCount(ctx, "x402:tx_window",
		fmt.Sprintf("%d", time.Now().Add(-time.Hour).UnixMilli()),
		"+inf").Result()

	agentWallets, _ := h.rdb.SMembers(ctx, "x402:agents").Result()
	agents := make([]models.AgentStats, 0, len(agentWallets))
	for _, wallet := range agentWallets {
		reqs, _ := h.rdb.HGet(ctx, "x402:agent:"+wallet, "requests").Int64()
		drops, _ := h.rdb.HGet(ctx, "x402:agent:"+wallet, "usdc_drops").Float64()
		rep, _ := h.rdb.HGet(ctx, "x402:agent:"+wallet, "reputation").Int64()
		ts, _ := h.rdb.HGet(ctx, "x402:agent:"+wallet, "last_seen").Int64()
		agents = append(agents, models.AgentStats{
			Wallet:     wallet,
			Requests:   reqs,
			USDCSpent:  dropsToUSDC(drops),
			Reputation: rep,
			LastSeen:   time.Unix(ts, 0),
		})
	}

	return models.StatsSnapshot{
		TotalUSDC:    dropsToUSDC(totalDrops),
		TotalTx:      totalTx,
		TxPerHour:    float64(txWindow),
		ActiveAgents: len(agents),
		Agents:       agents,
	}
}

func parseDrops(raw string) float64 {
	var f float64
	fmt.Sscanf(raw, "%f", &f)
	return f
}

func dropsToUSDC(drops float64) string {
	return fmt.Sprintf("%.6f", drops/1_000_000)
}
