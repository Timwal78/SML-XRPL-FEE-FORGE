// Package inference implements the BYOK (Bring Your Own Key) LLM proxy.
// The gateway injects the owner's AI provider credentials from environment
// variables into every request. Agents pay via x402 and receive inference;
// the operator never exposes their API keys to agents.
package inference

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/rs/zerolog/log"
)

const (
	anthropicMessagesURL  = "https://api.anthropic.com/v1/messages"
	openAICompletionsURL  = "https://api.openai.com/v1/chat/completions"
	anthropicVersion      = "2023-06-01"
	defaultAnthropicModel = "claude-sonnet-4-6"
)

// BYOKEngine proxies LLM requests injecting operator-owned API keys.
type BYOKEngine struct {
	anthropicKey string
	openAIKey    string
	provider     string // "anthropic" | "openai" | "auto"
	client       *http.Client
}

func NewBYOKEngine() *BYOKEngine {
	provider := os.Getenv("BYOK_PROVIDER")
	if provider == "" {
		provider = "auto"
	}
	return &BYOKEngine{
		anthropicKey: os.Getenv("ANTHROPIC_API_KEY"),
		openAIKey:    os.Getenv("OPENAI_API_KEY"),
		provider:     provider,
		client: &http.Client{
			Timeout: 120 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        50,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
			},
		},
	}
}

// HandleCompletions proxies OpenAI-style chat completions requests.
func (e *BYOKEngine) HandleCompletions(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		http.Error(w, `{"error":"failed to read request body"}`, http.StatusBadRequest)
		return
	}
	var reqBody map[string]interface{}
	if err := json.Unmarshal(body, &reqBody); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}
	switch e.selectProvider(reqBody) {
	case "anthropic":
		e.proxyAnthropic(w, r, reqBody)
	case "openai":
		e.proxyOpenAI(w, r, body)
	default:
		http.Error(w, `{"error":"no AI provider configured"}`, http.StatusServiceUnavailable)
	}
}

// HandleMessages proxies Anthropic-style /v1/messages requests directly.
func (e *BYOKEngine) HandleMessages(w http.ResponseWriter, r *http.Request) {
	if e.anthropicKey == "" {
		http.Error(w, `{"error":"anthropic key not configured"}`, http.StatusServiceUnavailable)
		return
	}
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		http.Error(w, `{"error":"failed to read body"}`, http.StatusBadRequest)
		return
	}
	var reqBody map[string]interface{}
	if err := json.Unmarshal(body, &reqBody); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}
	e.proxyAnthropic(w, r, reqBody)
}

func (e *BYOKEngine) proxyAnthropic(w http.ResponseWriter, r *http.Request, reqBody map[string]interface{}) {
	if e.anthropicKey == "" {
		http.Error(w, `{"error":"anthropic key not configured"}`, http.StatusServiceUnavailable)
		return
	}
	if _, ok := reqBody["model"]; !ok {
		reqBody["model"] = defaultAnthropicModel
	}
	if _, ok := reqBody["max_tokens"]; !ok {
		reqBody["max_tokens"] = 4096
	}
	payload, err := json.Marshal(reqBody)
	if err != nil {
		http.Error(w, `{"error":"marshal failed"}`, http.StatusInternalServerError)
		return
	}
	upstream, err := http.NewRequestWithContext(r.Context(), http.MethodPost, anthropicMessagesURL, bytes.NewReader(payload))
	if err != nil {
		http.Error(w, `{"error":"upstream request build failed"}`, http.StatusInternalServerError)
		return
	}
	upstream.Header.Set("Content-Type", "application/json")
	upstream.Header.Set("anthropic-version", anthropicVersion)
	upstream.Header.Set("x-api-key", e.anthropicKey)
	if accept := r.Header.Get("Accept"); accept != "" {
		upstream.Header.Set("Accept", accept)
	}
	e.proxyResponse(w, upstream, "anthropic")
}

func (e *BYOKEngine) proxyOpenAI(w http.ResponseWriter, r *http.Request, body []byte) {
	if e.openAIKey == "" {
		http.Error(w, `{"error":"openai key not configured"}`, http.StatusServiceUnavailable)
		return
	}
	upstream, err := http.NewRequestWithContext(r.Context(), http.MethodPost, openAICompletionsURL, bytes.NewReader(body))
	if err != nil {
		http.Error(w, `{"error":"upstream request build failed"}`, http.StatusInternalServerError)
		return
	}
	upstream.Header.Set("Content-Type", "application/json")
	upstream.Header.Set("Authorization", "Bearer "+e.openAIKey)
	e.proxyResponse(w, upstream, "openai")
}

func (e *BYOKEngine) proxyResponse(w http.ResponseWriter, req *http.Request, provider string) {
	resp, err := e.client.Do(req)
	if err != nil {
		log.Error().Err(err).Str("provider", provider).Msg("upstream inference error")
		http.Error(w, `{"error":"upstream inference failed"}`, http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	for k, vs := range resp.Header {
		for _, v := range vs {
			w.Header().Add(k, v)
		}
	}
	w.Header().Del("x-api-key")
	w.Header().Del("Authorization")
	w.Header().Set("X-BYOK-Provider", provider)
	w.WriteHeader(resp.StatusCode)
	if _, err := io.Copy(w, resp.Body); err != nil {
		log.Error().Err(err).Str("provider", provider).Msg("response copy error")
	}
}

func (e *BYOKEngine) selectProvider(body map[string]interface{}) string {
	switch e.provider {
	case "anthropic":
		if e.anthropicKey != "" {
			return "anthropic"
		}
	case "openai":
		if e.openAIKey != "" {
			return "openai"
		}
	case "auto":
		if model, ok := body["model"].(string); ok && strings.Contains(model, "claude") {
			if e.anthropicKey != "" {
				return "anthropic"
			}
		}
		if e.anthropicKey != "" {
			return "anthropic"
		}
		if e.openAIKey != "" {
			return "openai"
		}
	}
	return ""
}
