// Command server is the entry point for The Shadow Desk x402 API gateway.
// It wires all internal packages into a single HTTP server with graceful shutdown.
package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/alpha"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/billing"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/config"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/ingest"
	"github.com/timwal78/sml-xrpl-fee-forge/shadow-desk/mcp"
)

func main() {
	// JSON-structured logging so output integrates with GCP, Datadog, Render, etc.
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))

	cfg := config.Load()

	mux := http.NewServeMux()

	// POST /v1/ingest — TradingView Pine Script alert webhook.
	mux.HandleFunc("/v1/ingest", ingest.Handler(cfg.IngestSecret))

	// GET /v1/alpha/stream?ticker=<symbol> — x402-gated institutional alpha.
	mux.HandleFunc("/v1/alpha/stream", alpha.Handler(cfg))

	// GET /v1/admin/billing — settled payment ledger (admin-key protected).
	mux.HandleFunc("/v1/admin/billing", adminBillingHandler(cfg.AdminAPIKey))

	// GET /.well-known/mcp.json — MCP auto-discovery for autonomous AI agents.
	mux.HandleFunc("/.well-known/mcp.json", mcp.Handler())

	// GET /healthz — liveness probe for load balancers and uptime monitors.
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok","service":"shadow-desk"}`))
	})

	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Run the server in a background goroutine so the main goroutine can block
	// on OS signals for clean shutdown.
	go func() {
		slog.Info("Shadow Desk started", "port", cfg.Port,
			"facilitator", cfg.FacilitatorURL,
			"alpha_wallet", cfg.AlphaProviderWallet,
		)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("server crashed", "err", err)
			os.Exit(1)
		}
	}()

	// Block until SIGINT or SIGTERM, then drain in-flight requests.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	slog.Info("shutdown signal received — draining connections")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		slog.Error("graceful shutdown failed", "err", err)
	} else {
		slog.Info("server stopped cleanly")
	}
}

// adminBillingHandler returns a handler for GET /v1/admin/billing.
// Callers must provide the correct X-Admin-Key header when ADMIN_API_KEY is set.
func adminBillingHandler(adminKey string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if adminKey != "" && r.Header.Get("X-Admin-Key") != adminKey {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"error":"unauthorized"}`))
			return
		}

		events := billing.Default.All()
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(events); err != nil {
			slog.Error("encode billing response", "err", err)
		}
	}
}
