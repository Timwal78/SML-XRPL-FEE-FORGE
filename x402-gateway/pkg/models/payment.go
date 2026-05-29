package models

import "time"

// PaymentRequirements is the x402 payment details encoded in the X-PAYMENT-REQUIRED header.
type PaymentRequirements struct {
	Scheme             string      `json:"scheme"`
	Network            string      `json:"network"`
	MaxAmountRequired  string      `json:"maxAmountRequired"`
	Resource           string      `json:"resource"`
	Description        string      `json:"description"`
	MimeType           string      `json:"mimeType"`
	PayTo              string      `json:"payTo"`
	MaxTimeoutSeconds  int         `json:"maxTimeoutSeconds"`
	Asset              string      `json:"asset"`
	Extra              AssetExtra  `json:"extra"`
}

type AssetExtra struct {
	Name     string `json:"name"`
	Decimals int    `json:"decimals"`
}

// FacilitatorVerifyRequest is sent to POST https://x402.org/facilitator/verify.
type FacilitatorVerifyRequest struct {
	X402Version         int                 `json:"x402Version"`
	Payload             string              `json:"payload"`
	PaymentRequirements PaymentRequirements `json:"paymentRequirements"`
}

// FacilitatorVerifyResponse is returned by the facilitator /verify endpoint.
type FacilitatorVerifyResponse struct {
	IsValid bool   `json:"isValid"`
	InvalidReason string `json:"invalidReason,omitempty"`
	Payer   string `json:"payer,omitempty"`
}

// FacilitatorSettleRequest is sent to POST https://x402.org/facilitator/settle.
type FacilitatorSettleRequest struct {
	X402Version         int                 `json:"x402Version"`
	Payload             string              `json:"payload"`
	PaymentRequirements PaymentRequirements `json:"paymentRequirements"`
}

// FacilitatorSettleResponse is returned by the facilitator /settle endpoint.
type FacilitatorSettleResponse struct {
	Success     bool   `json:"success"`
	TxHash      string `json:"txHash,omitempty"`
	Network     string `json:"network,omitempty"`
	ErrorReason string `json:"errorReason,omitempty"`
}

// PaymentEvent is broadcast over SSE to the dashboard.
type PaymentEvent struct {
	Type        string    `json:"type"`
	Timestamp   time.Time `json:"timestamp"`
	Payer       string    `json:"payer"`
	AmountUSDC  string    `json:"amountUsdc"`
	TxHash      string    `json:"txHash"`
	Resource    string    `json:"resource"`
	XRPLTxHash  string    `json:"xrplTxHash,omitempty"`
}

// AgentStats tracks per-agent wallet metrics stored in Redis.
type AgentStats struct {
	Wallet      string    `json:"wallet"`
	Requests    int64     `json:"requests"`
	USDCSpent   string    `json:"usdcSpent"`
	Reputation  int64     `json:"reputation"`
	LastSeen    time.Time `json:"lastSeen"`
}

// XRPLNotaryEntry is a record of a trust transaction submitted to XRPL.
type XRPLNotaryEntry struct {
	Timestamp   time.Time `json:"timestamp"`
	AgentWallet string    `json:"agentWallet"`
	BaseTxHash  string    `json:"baseTxHash"`
	XRPLTxHash  string    `json:"xrplTxHash"`
	Memo        string    `json:"memo"`
}

// StatsSnapshot is the full state snapshot sent on SSE /api/stream connect.
type StatsSnapshot struct {
	TotalUSDC      string       `json:"totalUsdc"`
	TotalTx        int64        `json:"totalTx"`
	TxPerHour      float64      `json:"txPerHour"`
	ActiveAgents   int          `json:"activeAgents"`
	Agents         []AgentStats `json:"agents"`
	RecentNotary   []XRPLNotaryEntry `json:"recentNotary"`
}
