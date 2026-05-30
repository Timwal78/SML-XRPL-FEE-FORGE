package x402

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/rs/zerolog/log"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/stream"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/internal/xrpl"
	"github.com/timwal78/sml-xrpl-fee-forge/x402-gateway/pkg/models"
)

// USDC on Base mainnet (official Circle deployment)
const baseUSDCAsset = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

// Handler implements the x402 payment middleware.
type Handler struct {
	merchantWallet  string
	paymentAmount   string // in USDC micro-units, e.g. "500000" = $0.50
	facilitator     *Facilitator
	notary          *xrpl.Notary
	hub             *stream.Hub
	paymentRequired string // pre-computed Base64 header value
}

func NewHandler(merchantWallet string, facilitator *Facilitator, hub *stream.Hub) *Handler {
	amount := os.Getenv("PAYMENT_AMOUNT_USDC_DROPS")
	if amount == "" {
		amount = "500000" // $0.50 USDC (6 decimals)
	}
	h := &Handler{
		merchantWallet: merchantWallet,
		paymentAmount:  amount,
		facilitator:    facilitator,
		notary:         xrpl.NewNotary(),
		hub:            hub,
	}
	h.paymentRequired = h.buildPaymentRequired()
	return h
}

func (h *Handler) buildPaymentRequired() string {
	req := h.buildPaymentReqs()
	b, _ := json.Marshal(req)
	return base64.StdEncoding.EncodeToString(b)
}

// PaymentMiddleware checks for a valid X-PAYMENT header.
// Missing or invalid → returns 402 with X-PAYMENT-REQUIRED header.
// Valid + settled → continues to the next handler with X-PAYMENT-RESPONSE header.
func (h *Handler) PaymentMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paymentHeader := r.Header.Get("PAYMENT")
		if paymentHeader == "" {
			paymentHeader = r.Header.Get("X-PAYMENT") // Fallback
		}
		if paymentHeader == "" {
			h.require402(w)
			return
		}

		ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
		defer cancel()

		verifyResp, err := h.facilitator.Verify(ctx, paymentHeader, h.buildPaymentReqs())
		if err != nil {
			log.Error().Err(err).Msg("facilitator verify error")
			writeJSON(w, http.StatusPaymentRequired, map[string]string{"error": "payment_verification_failed"})
			return
		}
		if !verifyResp.IsValid {
			log.Warn().Str("reason", verifyResp.InvalidReason).Msg("payment invalid")
			w.Header().Set("PAYMENT-REQUIRED", h.paymentRequired)
			writeJSON(w, http.StatusPaymentRequired, map[string]string{
				"error":  "payment_invalid",
				"reason": verifyResp.InvalidReason,
			})
			return
		}

		settleResp, err := h.facilitator.Settle(ctx, paymentHeader, h.buildPaymentReqs())
		if err != nil {
			log.Error().Err(err).Msg("facilitator settle error")
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "settlement_failed_retry"})
			return
		}
		if !settleResp.Success {
			log.Error().Str("reason", settleResp.ErrorReason).Msg("settlement rejected")
			writeJSON(w, http.StatusPaymentRequired, map[string]string{
				"error":  "settlement_rejected",
				"reason": settleResp.ErrorReason,
			})
			return
		}

		log.Info().
			Str("payer", verifyResp.Payer).
			Str("tx_hash", settleResp.TxHash).
			Str("amount_drops", h.paymentAmount).
			Msg("payment settled")

		// Fire async Ghost Layer — never blocks the request path.
		go func() {
			notaryCtx, nc := context.WithTimeout(context.Background(), 20*time.Second)
			defer nc()
			xrplTxHash := h.notary.RecordTrust(notaryCtx, verifyResp.Payer, settleResp.TxHash)
			h.hub.IncrAgentReputation(notaryCtx, verifyResp.Payer)

			evt := models.PaymentEvent{
				Type:       "payment",
				Timestamp:  time.Now().UTC(),
				Payer:      verifyResp.Payer,
				AmountUSDC: dropsToUSDC(h.paymentAmount),
				TxHash:     settleResp.TxHash,
				Resource:   r.URL.Path,
				XRPLTxHash: xrplTxHash,
			}
			h.hub.Publish(map[string]interface{}{"type": "payment", "data": evt})
			h.hub.RecordPayment(notaryCtx, verifyResp.Payer, h.paymentAmount)
		}()

		paymentResponseB, _ := json.Marshal(map[string]string{
			"txHash":  settleResp.TxHash,
			"network": "base",
			"payer":   verifyResp.Payer,
		})
		w.Header().Set("PAYMENT-RESPONSE", base64.StdEncoding.EncodeToString(paymentResponseB))
		w.Header().Set("X-PAYMENT-RESPONSE", base64.StdEncoding.EncodeToString(paymentResponseB))
		next.ServeHTTP(w, r)
	})
}

func (h *Handler) require402(w http.ResponseWriter) {
	w.Header().Set("PAYMENT-REQUIRED", h.paymentRequired)
	writeJSON(w, http.StatusPaymentRequired, map[string]interface{}{
		"error":   "payment_required",
		"details": "Attach PAYMENT header with EIP-3009 transferWithAuthorization",
	})
}

func (h *Handler) buildPaymentReqs() models.PaymentRequiredV2 {
	return models.PaymentRequiredV2{
		X402Version: 2,
		Resource: models.ResourceV2{
			URL:         "/api/inference",
			Description: "AI Inference — x402 | SML XRPL Fee Forge",
			MimeType:    "application/json",
		},
		Accepts: []models.AcceptsV2{
			{
				Scheme:            "exact",
				Network:           "base",
				Asset:             baseUSDCAsset,
				Amount:            h.paymentAmount,
				PayTo:             h.merchantWallet,
				MaxTimeoutSeconds: 60,
				Extra:             models.AssetExtra{Name: "USDC", Decimals: 6},
			},
		},
		Extensions: models.ExtensionsV2{
			Bazaar: models.ExtensionsBazaar{
				BazaarResourceServerExtension: true,
				Info: models.BazaarInfo{
					Name:        "SML Forge Inference API",
					Description: "Premium AI inference for x402 agents",
				},
				Schema: map[string]interface{}{
					"type": "object",
					"properties": map[string]interface{}{
						"choices": map[string]interface{}{
							"type": "array",
							"items": map[string]interface{}{
								"type": "object",
							},
						},
					},
				},
			},
		},
	}
}

func dropsToUSDC(drops string) string {
	var v float64
	fmt.Sscanf(drops, "%f", &v)
	return fmt.Sprintf("%.6f", v/1_000_000)
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
