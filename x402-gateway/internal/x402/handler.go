package x402

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"os"
	"strings"
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
	paymentAmount   string // in USDC micro-units (drops), e.g. "500000" = $0.50
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
	req := models.PaymentRequirements{
		Scheme:            "exact",
		Network:           "base",
		MaxAmountRequired: h.paymentAmount,
		Resource:          "/api/inference",
		Description:       "AI Inference — powered by x402 | SML XRPL Fee Forge",
		MimeType:          "application/json",
		PayTo:             h.merchantWallet,
		MaxTimeoutSeconds: 60,
		Asset:             baseUSDCAsset,
		Extra: models.AssetExtra{
			Name:     "USDC",
			Decimals: 6,
		},
	}
	b, _ := json.Marshal(req)
	return base64.StdEncoding.EncodeToString(b)
}

// PaymentMiddleware checks for a valid X-PAYMENT header. If missing or
// invalid, returns 402 with PAYMENT-REQUIRED details. On success, continues
// to the next handler and attaches X-PAYMENT-RESPONSE.
func (h *Handler) PaymentMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paymentHeader := r.Header.Get("X-PAYMENT")
		if paymentHeader == "" {
			h.require402(w)
			return
		}

		ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
		defer cancel()

		verifyResp, err := h.facilitator.Verify(ctx, paymentHeader, h.buildPaymentReqs())
		if err != nil {
			log.Error().Err(err).Str("payer", sanitize(paymentHeader)).Msg("facilitator verify error")
			http.Error(w, `{"error":"payment verification failed"}`, http.StatusPaymentRequired)
			return
		}
		if !verifyResp.IsValid {
			log.Warn().Str("reason", verifyResp.InvalidReason).Msg("payment invalid")
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("X-PAYMENT-REQUIRED", h.paymentRequired)
			w.WriteHeader(http.StatusPaymentRequired)
			json.NewEncoder(w).Encode(map[string]string{
				"error":  "payment_invalid",
				"reason": verifyResp.InvalidReason,
			})
			return
		}

		settleResp, err := h.facilitator.Settle(ctx, paymentHeader, h.buildPaymentReqs())
		if err != nil {
			log.Error().Err(err).Msg("facilitator settle error")
			http.Error(w, `{"error":"settlement failed, please retry"}`, http.StatusServiceUnavailable)
			return
		}
		if !settleResp.Success {
			log.Error().Str("reason", settleResp.ErrorReason).Msg("settlement rejected")
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusPaymentRequired)
			json.NewEncoder(w).Encode(map[string]string{
				"error":  "settlement_failed",
				"reason": settleResp.ErrorReason,
			})
			return
		}

		log.Info().
			Str("payer", verifyResp.Payer).
			Str("tx_hash", settleResp.TxHash).
			Str("amount_drops", h.paymentAmount).
			Msg("payment settled")

		// Async: fire XRPL notary and stats update — never block the request.
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
		w.Header().Set("X-PAYMENT-RESPONSE", base64.StdEncoding.EncodeToString(paymentResponseB))

		next.ServeHTTP(w, r)
	})
}

func (h *Handler) require402(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-PAYMENT-REQUIRED", h.paymentRequired)
	w.WriteHeader(http.StatusPaymentRequired)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"error":   "payment_required",
		"details": "Attach X-PAYMENT header with EIP-3009 transferWithAuthorization signature",
		"x402Version": 1,
	})
}

func (h *Handler) buildPaymentReqs() models.PaymentRequirements {
	return models.PaymentRequirements{
		Scheme:            "exact",
		Network:           "base",
		MaxAmountRequired: h.paymentAmount,
		Resource:          "/api/inference",
		Description:       "AI Inference — powered by x402 | SML XRPL Fee Forge",
		MimeType:          "application/json",
		PayTo:             h.merchantWallet,
		MaxTimeoutSeconds: 60,
		Asset:             baseUSDCAsset,
		Extra: models.AssetExtra{Name: "USDC", Decimals: 6},
	}
}

func dropsToUSDC(drops string) string {
	var v float64
	if _, err := fmt.Sscanf(drops, "%f", &v); err == nil {
		return fmt.Sprintf("%.6f", v/1_000_000)
	}
	return "0.000000"
}

func sanitize(s string) string {
	if len(s) > 20 {
		return s[:20] + "..."
	}
	return s
}

func init() {
	// ensure fmt is imported
	_ = strings.Contains
}
