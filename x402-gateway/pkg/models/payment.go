package models

import "time"

// ResourceV2 defines the resource being protected.
type ResourceV2 struct {
	URL         string `json:"url"`
	Description string `json:"description"`
	MimeType    string `json:"mimeType"`
	Method      string `json:"method,omitempty"`
	ToolName    string `json:"toolName,omitempty"`
	ToolNameSnake string `json:"tool_name,omitempty"`
}

// AcceptsV2 defines an accepted payment method.
type AcceptsV2 struct {
	Scheme            string     `json:"scheme"`
	Network           string     `json:"network"`
	Asset             string     `json:"asset"`
	Amount            string     `json:"amount"`
	PayTo             string     `json:"payTo"`
	MaxTimeoutSeconds int        `json:"maxTimeoutSeconds"`
	Extra             AssetExtra `json:"extra"`
}

// BazaarInfo contains discovery metadata.
type BazaarInfo struct {
	Name          string                 `json:"name"`
	Title         string                 `json:"title,omitempty"`
	Description   string                 `json:"description"`
	Method        string                 `json:"method,omitempty"`
	ToolName      string                 `json:"toolName,omitempty"`
	ToolNameSnake string                 `json:"tool_name,omitempty"`
	InputSchema   map[string]interface{} `json:"inputSchema,omitempty"`
	Output        map[string]interface{} `json:"output,omitempty"`
}

// ExtensionsBazaar contains Bazaar discovery metadata.
type ExtensionsBazaar struct {
	BazaarResourceServerExtension bool                   `json:"bazaarResourceServerExtension"`
	ToolName                      string                 `json:"toolName,omitempty"`
	ToolNameSnake                 string                 `json:"tool_name,omitempty"`
	Method                        string                 `json:"method,omitempty"`
	Info                          BazaarInfo             `json:"info"`
	Schema                        map[string]interface{} `json:"schema,omitempty"`
}

// ExtensionsV2 contains optional x402 extensions.
type ExtensionsV2 struct {
	Bazaar ExtensionsBazaar `json:"bazaar"`
}

// PaymentRequiredV2 is the x402 v2 payload encoded in the PAYMENT-REQUIRED header.
type PaymentRequiredV2 struct {
	X402Version int          `json:"x402Version"`
	Resource    ResourceV2   `json:"resource"`
	Accepts     []AcceptsV2  `json:"accepts"`
	Extensions  ExtensionsV2 `json:"extensions"`
}

type AssetExtra struct {
	Name     string `json:"name"`
	Decimals int    `json:"decimals"`
}

// FacilitatorVerifyRequest is sent to POST https://x402.org/facilitator/verify.
type FacilitatorVerifyRequest struct {
	X402Version         int               `json:"x402Version"`
	Payload             string            `json:"payload"`
	PaymentRequirements PaymentRequiredV2 `json:"paymentRequirements"`
}

// FacilitatorVerifyResponse is returned by the facilitator /verify endpoint.
type FacilitatorVerifyResponse struct {
	IsValid       bool   `json:"isValid"`
	InvalidReason string `json:"invalidReason,omitempty"`
	Payer         string `json:"payer,omitempty"`
}

// FacilitatorSettleRequest is sent to POST https://x402.org/facilitator/settle.
type FacilitatorSettleRequest struct {
	X402Version         int               `json:"x402Version"`
	Payload             string            `json:"payload"`
	PaymentRequirements PaymentRequiredV2 `json:"paymentRequirements"`
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
