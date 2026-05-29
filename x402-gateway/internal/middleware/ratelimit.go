// Package middleware provides a per-agent-wallet Redis sliding-window rate limiter.
package middleware

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
)

// WalletRateLimiter enforces a sliding-window rate limit per agent wallet address.
// The wallet address is extracted from the X-PAYMENT header (base64 JSON payload).
// Falls back to IP-based limiting when the wallet cannot be parsed.
type WalletRateLimiter struct {
	rdb    *redis.Client
	limit  int
	window time.Duration
}

func NewWalletRateLimiter(rdb *redis.Client) *WalletRateLimiter {
	limitStr := os.Getenv("RATE_LIMIT_RPM")
	limit := 60
	if v, err := strconv.Atoi(limitStr); err == nil && v > 0 {
		limit = v
	}
	return &WalletRateLimiter{
		rdb:    rdb,
		limit:  limit,
		window: time.Minute,
	}
}

func (rl *WalletRateLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		identity := rl.extractIdentity(r)
		key := "x402:ratelimit:" + identity
		now := time.Now()
		windowStart := now.Add(-rl.window).UnixMilli()

		ctx := r.Context()

		// Lua script: atomic sliding window counter.
		// Removes expired entries, counts remaining, conditionally adds current.
		script := redis.NewScript(`
			local key = KEYS[1]
			local now = tonumber(ARGV[1])
			local window_start = tonumber(ARGV[2])
			local limit = tonumber(ARGV[3])
			local expire_ms = tonumber(ARGV[4])
			redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
			local count = redis.call('ZCARD', key)
			if count < limit then
				redis.call('ZADD', key, now, now)
				redis.call('PEXPIRE', key, expire_ms)
				return 0
			end
			return count
		`)

		result, err := script.Run(ctx, rl.rdb,
			[]string{key},
			now.UnixMilli(),
			windowStart,
			rl.limit,
			rl.window.Milliseconds(),
		).Int64()
		if err != nil {
			// On Redis error, fail open to avoid blocking legitimate traffic.
			log.Error().Err(err).Str("identity", identity).Msg("rate limit redis error, failing open")
			next.ServeHTTP(w, r)
			return
		}

		if result > 0 {
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("Retry-After", "60")
			w.Header().Set("X-RateLimit-Limit", strconv.Itoa(rl.limit))
			w.Header().Set("X-RateLimit-Remaining", "0")
			w.WriteHeader(http.StatusTooManyRequests)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error":       "rate_limit_exceeded",
				"limit":       rl.limit,
				"window":      "1m",
				"retry_after": 60,
			})
			return
		}

		w.Header().Set("X-RateLimit-Limit", strconv.Itoa(rl.limit))
		next.ServeHTTP(w, r)
	})
}

// extractIdentity returns the agent wallet address from the X-PAYMENT header
// or falls back to the client IP.
func (rl *WalletRateLimiter) extractIdentity(r *http.Request) string {
	paymentHeader := r.Header.Get("X-PAYMENT")
	if paymentHeader == "" {
		return ipIdentity(r)
	}

	// X-PAYMENT is a base64-encoded JSON object. We only need the "from" field
	// which contains the agent's EVM wallet address.
	b, err := base64.StdEncoding.DecodeString(paymentHeader)
	if err != nil {
		// try raw JSON (some implementations don't base64 the outer envelope)
		b = []byte(paymentHeader)
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(b, &payload); err != nil {
		return ipIdentity(r)
	}

	// Check common field names for the payer address.
	for _, field := range []string{"from", "payer", "authorization", "owner"} {
		if v, ok := payload[field].(string); ok && len(v) == 42 {
			return "wallet:" + v
		}
	}

	// If we have an authorization sub-object (EIP-3009 structure)
	if auth, ok := payload["authorization"].(map[string]interface{}); ok {
		if from, ok := auth["from"].(string); ok {
			return "wallet:" + from
		}
	}

	return ipIdentity(r)
}

func ipIdentity(r *http.Request) string {
	ip := r.Header.Get("X-Real-IP")
	if ip == "" {
		ip = r.Header.Get("X-Forwarded-For")
	}
	if ip == "" {
		ip = r.RemoteAddr
	}
	return fmt.Sprintf("ip:%s", ip)
}
