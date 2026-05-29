package x402

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/rs/zerolog/log"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/pkg/models"
)

// Facilitator wraps the x402.org/facilitator HTTP API.
type Facilitator struct {
	baseURL string
	client  *http.Client
}

func NewFacilitator(baseURL string) *Facilitator {
	return &Facilitator{
		baseURL: baseURL,
		client: &http.Client{
			Timeout: 30 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 20,
				IdleConnTimeout:     90 * time.Second,
			},
		},
	}
}

// Verify calls POST /verify on the facilitator and returns validation result.
func (f *Facilitator) Verify(ctx context.Context, paymentHeader string, reqs models.PaymentRequirements) (*models.FacilitatorVerifyResponse, error) {
	body := models.FacilitatorVerifyRequest{
		X402Version:         1,
		Payload:             paymentHeader,
		PaymentRequirements: reqs,
	}
	resp, err := f.post(ctx, "/verify", body)
	if err != nil {
		return nil, fmt.Errorf("facilitator /verify: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		rawBody, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		log.Error().Int("status", resp.StatusCode).Str("body", string(rawBody)).Msg("facilitator /verify non-200")
		return nil, fmt.Errorf("facilitator /verify returned HTTP %d", resp.StatusCode)
	}

	var result models.FacilitatorVerifyResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("facilitator /verify decode: %w", err)
	}
	log.Debug().Bool("valid", result.IsValid).Str("payer", result.Payer).Msg("facilitator verify response")
	return &result, nil
}

// Settle calls POST /settle on the facilitator and returns settlement result.
func (f *Facilitator) Settle(ctx context.Context, paymentHeader string, reqs models.PaymentRequirements) (*models.FacilitatorSettleResponse, error) {
	body := models.FacilitatorSettleRequest{
		X402Version:         1,
		Payload:             paymentHeader,
		PaymentRequirements: reqs,
	}
	resp, err := f.post(ctx, "/settle", body)
	if err != nil {
		return nil, fmt.Errorf("facilitator /settle: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		rawBody, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		log.Error().Int("status", resp.StatusCode).Str("body", string(rawBody)).Msg("facilitator /settle non-200")
		return nil, fmt.Errorf("facilitator /settle returned HTTP %d", resp.StatusCode)
	}

	var result models.FacilitatorSettleResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("facilitator /settle decode: %w", err)
	}
	log.Info().Bool("success", result.Success).Str("tx", result.TxHash).Msg("facilitator settle response")
	return &result, nil
}

func (f *Facilitator) post(ctx context.Context, path string, payload interface{}) (*http.Response, error) {
	b, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, f.baseURL+path, bytes.NewReader(b))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "sml-xrpl-fee-forge/x402-gateway")
	return f.client.Do(req)
}
