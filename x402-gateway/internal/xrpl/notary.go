// Package xrpl implements the Ghost Layer: an async XRPL trust/reputation notary.
// After every successful x402 USDC settlement on Base, this package submits a
// lightweight Memo transaction to XRPL that acts as an on-chain Agent Credit Bureau
// entry for the paying agent's EVM address.
package xrpl

import (
	"bytes"
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/rs/zerolog/log"
)

const (
	xrplRPCMainnet = "https://xrplcluster.com"
	xrplRPCTestnet = "https://s.altnet.rippletest.net:51234"
	memoType       = "786402416765637443726564697442757265617500" // hex("x402AgentCreditBureau")
)

// Notary submits XRPL trust transactions asynchronously.
type Notary struct {
	rpcURL      string
	wallet      string // XRPL wallet address
	seed        string // XRPL wallet seed (Family Seed format)
	client      *http.Client
}

func NewNotary() *Notary {
	rpcURL := os.Getenv("XRPL_RPC_URL")
	if rpcURL == "" {
		if os.Getenv("XRPL_NETWORK") == "mainnet" {
			rpcURL = xrplRPCMainnet
		} else {
			rpcURL = xrplRPCTestnet
		}
	}
	return &Notary{
		rpcURL: rpcURL,
		wallet: os.Getenv("XRPL_NOTARY_WALLET_ADDRESS"),
		seed:   os.Getenv("XRPL_NOTARY_WALLET_SEED"),
		client: &http.Client{Timeout: 20 * time.Second},
	}
}

// RecordTrust submits a Memo-carrying Payment to XRPL that logs the agent's
// EVM address and the Base settlement tx hash as a reputation event.
// Returns the XRPL tx hash on success, or empty string on failure (non-fatal).
func (n *Notary) RecordTrust(ctx context.Context, agentEVMAddr, baseTxHash string) string {
	if n.wallet == "" || n.seed == "" {
		log.Warn().Msg("xrpl notary: wallet not configured, skipping")
		return ""
	}

	seq, fee, err := n.getAccountInfo(ctx)
	if err != nil {
		log.Error().Err(err).Msg("xrpl notary: account_info failed")
		return ""
	}

	memoData := buildMemoData(agentEVMAddr, baseTxHash)
	txBlob, txHash, err := n.signPayment(seq, fee, memoData)
	if err != nil {
		log.Error().Err(err).Msg("xrpl notary: sign failed")
		return ""
	}

	submitHash, err := n.submitTx(ctx, txBlob)
	if err != nil {
		log.Error().Err(err).Str("tx_hash", txHash).Msg("xrpl notary: submit failed")
		return ""
	}

	log.Info().
		Str("agent", agentEVMAddr).
		Str("base_tx", baseTxHash).
		Str("xrpl_tx", submitHash).
		Msg("xrpl notary: trust recorded")
	return submitHash
}

func (n *Notary) getAccountInfo(ctx context.Context) (seq uint32, fee string, err error) {
	payload := map[string]interface{}{
		"method": "account_info",
		"params": []map[string]interface{}{
			{"account": n.wallet, "ledger_index": "current"},
		},
	}
	resp, err := n.rpcCall(ctx, payload)
	if err != nil {
		return 0, "", err
	}
	result, ok := resp["result"].(map[string]interface{})
	if !ok {
		return 0, "", fmt.Errorf("unexpected account_info response")
	}
	acctData, ok := result["account_data"].(map[string]interface{})
	if !ok {
		return 0, "", fmt.Errorf("no account_data in response")
	}
	seqFloat, _ := acctData["Sequence"].(float64)
	seq = uint32(seqFloat)

	// Use a fixed fee of 12 drops (above the minimum 10-drop network fee)
	fee = "12"
	return seq, fee, nil
}

// signPayment builds and signs the XRPL Payment transaction using the XRPL
// JSON-RPC sign method. This requires the node to have signing enabled OR
// we use the sign_for/submit_multisigned path. For single-key wallets,
// sign via JSON-RPC is sufficient.
func (n *Notary) signPayment(seq uint32, fee string, memoData string) (txBlob, txHash string, err error) {
	// Build a self-payment (wallet -> wallet) of 1 drop XRP carrying the memo.
	// This is the cheapest possible XRPL transaction and leaves a permanent record.
	tx := map[string]interface{}{
		"TransactionType": "Payment",
		"Account":         n.wallet,
		"Destination":     n.wallet,
		"Amount":          "1", // 1 drop = 0.000001 XRP
		"Fee":             fee,
		"Sequence":        seq,
		"Memos": []map[string]interface{}{
			{
				"Memo": map[string]interface{}{
					"MemoType": strings.ToUpper(hex.EncodeToString([]byte("x402AgentCreditBureau"))),
					"MemoData": memoData,
				},
			},
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	payload := map[string]interface{}{
		"method": "sign",
		"params": []map[string]interface{}{
			{
				"tx_json": tx,
				"secret":  n.seed,
			},
		},
	}
	resp, err := n.rpcCall(ctx, payload)
	if err != nil {
		return "", "", err
	}
	result, ok := resp["result"].(map[string]interface{})
	if !ok {
		return "", "", fmt.Errorf("unexpected sign response")
	}
	txBlob, _ = result["tx_blob"].(string)
	txJSON, _ := result["tx_json"].(map[string]interface{})
	if txJSON != nil {
		txHash, _ = txJSON["hash"].(string)
	}
	if txBlob == "" {
		return "", "", fmt.Errorf("sign returned empty tx_blob; check node supports sign method")
	}
	return txBlob, txHash, nil
}

func (n *Notary) submitTx(ctx context.Context, txBlob string) (string, error) {
	payload := map[string]interface{}{
		"method": "submit",
		"params": []map[string]interface{}{
			{"tx_blob": txBlob},
		},
	}
	resp, err := n.rpcCall(ctx, payload)
	if err != nil {
		return "", err
	}
	result, ok := resp["result"].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("unexpected submit response")
	}
	engineResult, _ := result["engine_result"].(string)
	if engineResult != "tesSUCCESS" && !strings.HasPrefix(engineResult, "ter") {
		return "", fmt.Errorf("submit engine_result=%s", engineResult)
	}
	txJSON, _ := result["tx_json"].(map[string]interface{})
	hash := ""
	if txJSON != nil {
		hash, _ = txJSON["hash"].(string)
	}
	return hash, nil
}

func (n *Notary) rpcCall(ctx context.Context, payload interface{}) (map[string]interface{}, error) {
	b, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, n.rpcURL, bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := n.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

func buildMemoData(agentEVMAddr, baseTxHash string) string {
	data := fmt.Sprintf("%s|%s|%d", agentEVMAddr, baseTxHash, time.Now().Unix())
	return strings.ToUpper(hex.EncodeToString([]byte(data)))
}
