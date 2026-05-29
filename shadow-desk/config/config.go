// Package config loads all runtime configuration from environment variables.
package config

import (
	"log/slog"
	"os"
	"strings"
)

// Config holds every tunable value the gateway needs at runtime.
// All fields are populated from environment variables; no config files are read.
type Config struct {
	Port                string
	IngestSecret        string
	AlphaProviderWallet string
	PlatformWallet      string
	FacilitatorURL      string
	AdminAPIKey         string
}

// Load reads environment variables and returns a validated Config.
// Missing required values are logged as warnings; the server still starts
// with safe placeholder defaults so local development isn't blocked.
func Load() *Config {
	cfg := &Config{
		Port:                getEnv("PORT", "8080"),
		IngestSecret:        getEnv("INGEST_SECRET", ""),
		AlphaProviderWallet: getEnv("ALPHA_PROVIDER_WALLET", ""),
		PlatformWallet:      getEnv("PLATFORM_WALLET", ""),
		FacilitatorURL:      getEnv("FACILITATOR_URL", "https://x402.org/facilitator"),
		AdminAPIKey:         getEnv("ADMIN_API_KEY", ""),
	}
	cfg.validate()
	return cfg
}

func (c *Config) validate() {
	if c.IngestSecret == "" {
		slog.Warn("INGEST_SECRET not set — ingest endpoint accepts any payload")
	}
	if c.AlphaProviderWallet == "" {
		slog.Warn("ALPHA_PROVIDER_WALLET not set — using zero-address placeholder")
		c.AlphaProviderWallet = "0x0000000000000000000000000000000000000001"
	}
	if c.PlatformWallet == "" {
		slog.Warn("PLATFORM_WALLET not set — using zero-address placeholder")
		c.PlatformWallet = "0x0000000000000000000000000000000000000002"
	}
	if c.AdminAPIKey == "" {
		slog.Warn("ADMIN_API_KEY not set — billing endpoint is publicly readable")
	}
}

func getEnv(key, defaultVal string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return defaultVal
}
