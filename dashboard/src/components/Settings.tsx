import { useState } from 'react'

interface EnvVar {
  key: string
  label: string
  description: string
  secret: boolean
  group: string
}

const ENV_VARS: EnvVar[] = [
  // Payment
  { key: 'MERCHANT_WALLET_ADDRESS', label: 'Merchant Wallet', description: 'EVM address to receive USDC on Base', secret: false, group: 'Payment' },
  { key: 'PAYMENT_AMOUNT_USDC_DROPS', label: 'Price (USDC drops)', description: '500000 = $0.50 USDC (6 decimals)', secret: false, group: 'Payment' },
  { key: 'X402_FACILITATOR_URL', label: 'Facilitator URL', description: 'x402.org/facilitator or self-hosted', secret: false, group: 'Payment' },
  // AI Provider
  { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', description: 'sk-ant-... injected into every inference request', secret: true, group: 'BYOK' },
  { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', description: 'sk-... fallback provider', secret: true, group: 'BYOK' },
  { key: 'BYOK_PROVIDER', label: 'Default Provider', description: 'auto | anthropic | openai', secret: false, group: 'BYOK' },
  // XRPL
  { key: 'XRPL_NOTARY_WALLET_ADDRESS', label: 'XRPL Notary Wallet', description: 'r... address sending trust memos', secret: false, group: 'XRPL' },
  { key: 'XRPL_NOTARY_WALLET_SEED', label: 'XRPL Notary Seed', description: 's... family seed (mainnet/testnet)', secret: true, group: 'XRPL' },
  { key: 'XRPL_NETWORK', label: 'XRPL Network', description: 'testnet | mainnet', secret: false, group: 'XRPL' },
  // Rate limiting
  { key: 'RATE_LIMIT_RPM', label: 'Rate Limit (req/min)', description: 'Per-agent sliding window limit', secret: false, group: 'Gateway' },
  { key: 'PORT', label: 'Gateway Port', description: 'HTTP listen port (default 8080)', secret: false, group: 'Gateway' },
  { key: 'REDIS_URL', label: 'Redis URL', description: 'redis://host:6379', secret: false, group: 'Gateway' },
]

const GROUPS = ['Payment', 'BYOK', 'XRPL', 'Gateway']

const GROUP_COLORS: Record<string, string> = {
  Payment: 'neon-text-cyan',
  BYOK:    'neon-text-amber',
  XRPL:    'neon-text-green',
  Gateway: 'neon-text-magenta',
}

export default function Settings() {
  const [revealed, setRevealed] = useState<Set<string>>(new Set())

  const toggle = (key: string) => {
    setRevealed(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold neon-text-amber tracking-wider">GATEWAY SETTINGS</h1>
        <p className="text-xs text-terminal-dim mt-0.5">
          All values are server-side environment variables. Secrets are never stored in the browser.
        </p>
      </div>

      {/* Security notice */}
      <div className="panel border-neon-amber/30 bg-neon-amber/5">
        <div className="flex items-start gap-3">
          <span className="text-neon-amber text-base mt-0.5">⚠</span>
          <p className="text-xs text-terminal-dim leading-relaxed">
            This settings page is informational only — it shows the expected env var names and
            descriptions. Configure values in your <code className="text-neon-amber">.env</code> file or
            deployment secrets manager. API keys are injected at runtime and never transmitted to agents.
          </p>
        </div>
      </div>

      {GROUPS.map(group => (
        <div key={group} className="space-y-3">
          <h2 className={`text-xs font-bold uppercase tracking-widest ${GROUP_COLORS[group]}`}>{group}</h2>
          <div className="space-y-2">
            {ENV_VARS.filter(v => v.group === group).map(v => (
              <div key={v.key} className="panel flex flex-col sm:flex-row sm:items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <code className="text-neon-cyan text-xs">{v.key}</code>
                    {v.secret && (
                      <span className="badge bg-neon-red/10 text-neon-red border border-neon-red/30 text-xs">
                        SECRET
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-terminal-dim">{v.description}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <code className="text-xs px-2 py-1 bg-terminal-muted rounded-sm text-terminal-dim">
                    {v.secret
                      ? (revealed.has(v.key) ? `${v.label}` : '•••••••••••••••')
                      : v.label}
                  </code>
                  {v.secret && (
                    <button
                      onClick={() => toggle(v.key)}
                      className="text-xs text-terminal-dim hover:text-neon-cyan transition-colors px-2 py-1 border border-terminal-border hover:border-neon-cyan/30 rounded-sm"
                    >
                      {revealed.has(v.key) ? 'HIDE' : 'REVEAL'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* .env.example download hint */}
      <div className="panel border-terminal-border">
        <p className="text-xs text-terminal-dim">
          Copy <code className="text-neon-cyan">x402-gateway/.env.example</code> to <code className="text-neon-cyan">x402-gateway/.env</code> and
          populate all values before running <code className="text-neon-amber">make run</code> or <code className="text-neon-amber">docker compose up</code>.
        </p>
      </div>
    </div>
  )
}
