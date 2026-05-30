package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	chiMiddleware "github.com/go-chi/chi/v5/middleware"
	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/inference"
	ratelimit "github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/middleware"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/stream"
	x402 "github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/x402"
)

func main() {
	_ = godotenv.Load()

	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr, TimeFormat: time.RFC3339})

	port := mustEnv("PORT")
	redisURL := mustEnv("REDIS_URL")
	merchantWallet := mustEnv("MERCHANT_WALLET_ADDRESS")
	facilitatorURL := getEnvOr("X402_FACILITATOR_URL", "https://x402.org/facilitator")

	rdb := newRedisClient(redisURL)
	defer rdb.Close()

	pingCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := rdb.Ping(pingCtx).Err(); err != nil {
		log.Fatal().Err(err).Str("url", redisURL).Msg("redis unreachable")
	}

	hub := stream.NewHub(rdb)
	go hub.Run()

	facilitator := x402.NewFacilitator(facilitatorURL)
	handler := x402.NewHandler(merchantWallet, facilitator, hub)
	rateLimiter := ratelimit.NewWalletRateLimiter(rdb)
	byok := inference.NewBYOKEngine()

	r := chi.NewRouter()
	r.Use(chiMiddleware.RequestID)
	r.Use(chiMiddleware.RealIP)
	r.Use(chiMiddleware.Recoverer)
	r.Use(chiMiddleware.Timeout(90 * time.Second))
	r.Use(corsMiddleware)

	r.Get("/health", healthHandler)
	r.Get("/api/stream", hub.ServeSSE)
	r.Get("/api/admin/stats", hub.HandleStats)

	// Discoverable root endpoint for x402 validators
	r.With(handler.PaymentMiddleware).Get("/", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"service": "x402-gateway", "status": "payment_required_for_full_access"}`))
	})

	r.Get("/.well-known/mcp.json", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"schema_version": "mcp/1.0",
			"name": "x402-gateway",
			"description": "SML Forge Gateway for XRPL and Base",
			"tools": [
				{
					"name": "sml_forge_inference",
					"method": "POST",
					"toolName": "sml_forge_inference",
					"tool_name": "sml_forge_inference",
					"description": "Premium AI inference for x402 agents",
					"inputSchema": {
						"type": "object",
						"properties": {
							"model": { "type": "string" },
							"messages": { "type": "array" }
						}
					}
				}
			]
		}`))
	})

	r.Get("/.well-known/x402.json", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"name": "x402-gateway",
			"method": "POST",
			"toolName": "sml_forge_inference",
			"tool_name": "sml_forge_inference",
			"tools": [
				{
					"name": "sml_forge_inference",
					"method": "POST",
					"toolName": "sml_forge_inference",
					"tool_name": "sml_forge_inference",
					"description": "Premium AI inference for x402 agents",
					"inputSchema": {
						"type": "object",
						"properties": {
							"model": { "type": "string" },
							"messages": { "type": "array" }
						}
					}
				}
			]
		}`))
	})

	r.Route("/api/inference", func(r chi.Router) {
		r.Use(rateLimiter.Middleware)
		r.Use(handler.PaymentMiddleware)
		r.Post("/completions", byok.HandleCompletions)
		r.Post("/messages", byok.HandleMessages)
	})

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 90 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Info().Str("port", port).Str("merchant", merchantWallet).Msg("x402 gateway listening")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("server error")
		}
	}()

	<-quit
	log.Info().Msg("graceful shutdown initiated")
	shutCtx, shutCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutCancel()
	if err := srv.Shutdown(shutCtx); err != nil {
		log.Error().Err(err).Msg("shutdown error")
	}
	log.Info().Msg("server stopped")
}

func newRedisClient(url string) *redis.Client {
	opts, err := redis.ParseURL(url)
	if err != nil {
		// fallback: treat as host:port
		opts = &redis.Options{Addr: url}
	}
	return redis.NewClient(opts)
}

func mustEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		log.Fatal().Str("key", key).Msg("required env var missing")
	}
	return v
}

func getEnvOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, `{"status":"ok","service":"x402-gateway"}`)
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, PAYMENT, X-PAYMENT, Authorization")
		w.Header().Set("Access-Control-Expose-Headers", "PAYMENT-REQUIRED, PAYMENT-RESPONSE, X-PAYMENT-REQUIRED, X-PAYMENT-RESPONSE")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
