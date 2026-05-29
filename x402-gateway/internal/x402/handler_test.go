package x402_test

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/redis/go-redis/v9"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/stream"
	x402 "github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/x402"
)

func newTestHandler() *x402.Handler {
	rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	hub := stream.NewHub(rdb)
	go hub.Run()
	facilitator := x402.NewFacilitator("https://x402.org/facilitator")
	return x402.NewHandler("0xDeaD0000000000000000000000000000DeaDBeEf", facilitator, hub)
}

func TestPaymentMiddleware_Missing_Returns402(t *testing.T) {
	h := newTestHandler()
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	rr := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/inference/completions", strings.NewReader(`{}`))
	h.PaymentMiddleware(next).ServeHTTP(rr, req)

	if rr.Code != http.StatusPaymentRequired {
		t.Fatalf("expected 402, got %d", rr.Code)
	}

	paymentRequired := rr.Header().Get("X-PAYMENT-REQUIRED")
	if paymentRequired == "" {
		t.Fatal("expected X-PAYMENT-REQUIRED header to be set")
	}

	decoded, err := base64.StdEncoding.DecodeString(paymentRequired)
	if err != nil {
		t.Fatalf("X-PAYMENT-REQUIRED not valid base64: %v", err)
	}

	var reqs map[string]interface{}
	if err := json.Unmarshal(decoded, &reqs); err != nil {
		t.Fatalf("X-PAYMENT-REQUIRED not valid JSON: %v", err)
	}

	if reqs["scheme"] != "exact" {
		t.Errorf("expected scheme=exact, got %v", reqs["scheme"])
	}
	if reqs["network"] != "base" {
		t.Errorf("expected network=base, got %v", reqs["network"])
	}
	if reqs["asset"] != "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" {
		t.Errorf("unexpected asset: %v", reqs["asset"])
	}
}

func TestPaymentRequiredHeaderIsValidBase64JSON(t *testing.T) {
	h := newTestHandler()
	rr := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/inference/completions", nil)
	h.PaymentMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {})).ServeHTTP(rr, req)

	header := rr.Header().Get("X-PAYMENT-REQUIRED")
	if header == "" {
		t.Fatal("missing X-PAYMENT-REQUIRED")
	}
	b, err := base64.StdEncoding.DecodeString(header)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	var m map[string]interface{}
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	requiredFields := []string{"scheme", "network", "maxAmountRequired", "payTo", "asset", "extra"}
	for _, f := range requiredFields {
		if _, ok := m[f]; !ok {
			t.Errorf("missing field %q in PAYMENT-REQUIRED JSON", f)
		}
	}
}
