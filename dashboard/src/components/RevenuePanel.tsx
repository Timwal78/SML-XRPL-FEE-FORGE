import { useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { StatsSnapshot, PaymentEvent } from '../types'

interface Props {
  snapshot: StatsSnapshot | null
  feed: PaymentEvent[]
}

export default function RevenuePanel({ snapshot, feed }: Props) {
  const chartData = useMemo(() => {
    if (!feed.length) return []
    const buckets: Record<string, number> = {}
    feed.forEach(evt => {
      const d = new Date(evt.timestamp)
      const key = `${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`
      buckets[key] = (buckets[key] ?? 0) + parseFloat(evt.amountUsdc)
    })
    return Object.entries(buckets)
      .slice(-20)
      .map(([time, usdc]) => ({ time, usdc: +usdc.toFixed(4) }))
  }, [feed])

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold neon-text-cyan tracking-wider">REVENUE COMMAND</h1>
          <p className="text-xs text-terminal-dim mt-0.5">Real-time USDC settlement via x402 · Base Network</p>
        </div>
        <div className="text-xs text-terminal-dim font-mono">
          {new Date().toISOString().replace('T', ' ').slice(0, 19)} UTC
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total USDC Earned"
          value={snapshot ? `$${parseFloat(snapshot.totalUsdc).toFixed(4)}` : '—'}
          color="cyan"
        />
        <StatCard
          label="Total Transactions"
          value={snapshot ? snapshot.totalTx.toLocaleString() : '—'}
          color="green"
        />
        <StatCard
          label="Tx / Hour"
          value={snapshot ? snapshot.txPerHour.toFixed(1) : '—'}
          color="amber"
        />
        <StatCard
          label="Active Agents"
          value={snapshot ? snapshot.activeAgents.toString() : '—'}
          color="magenta"
        />
      </div>

      {/* Revenue chart */}
      <div className="panel">
        <div className="text-xs text-terminal-dim uppercase tracking-widest mb-4">USDC Flow (last 20 min)</div>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="usdcGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00FFFF" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00FFFF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fill: '#666', fontSize: 10, fontFamily: 'monospace' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#666', fontSize: 10, fontFamily: 'monospace' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#0d0d0d', border: '1px solid #1a1a1a', color: '#00FFFF', fontFamily: 'monospace', fontSize: 11 }}
                formatter={(v: number) => [`$${v.toFixed(4)}`, 'USDC']}
              />
              <Area type="monotone" dataKey="usdc" stroke="#00FFFF" strokeWidth={2} fill="url(#usdcGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-44 flex items-center justify-center text-terminal-dim text-xs">Awaiting transactions…</div>
        )}
      </div>

      {/* Live feed */}
      <div className="panel">
        <div className="text-xs text-terminal-dim uppercase tracking-widest mb-3">LIVE TRANSACTION FEED</div>
        <div className="space-y-px max-h-80 overflow-y-auto">
          {feed.length === 0 && (
            <div className="text-terminal-dim text-xs py-4 text-center">No transactions yet</div>
          )}
          {feed.map((evt, i) => (
            <FeedRow key={i} evt={evt} />
          ))}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  const colorMap: Record<string, string> = {
    cyan:    'neon-text-cyan',
    green:   'neon-text-green',
    magenta: 'neon-text-magenta',
    amber:   'neon-text-amber',
  }
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${colorMap[color] ?? 'text-terminal-text'}`}>{value}</div>
    </div>
  )
}

function FeedRow({ evt }: { evt: PaymentEvent }) {
  const shortWallet = `${evt.payer.slice(0, 6)}…${evt.payer.slice(-4)}`
  const time = new Date(evt.timestamp).toLocaleTimeString()
  return (
    <div className="table-row flex items-center gap-4 px-3 py-2 text-xs animate-slide-in">
      <span className="text-terminal-dim w-16 flex-shrink-0">{time}</span>
      <span className="text-neon-cyan font-mono w-24 flex-shrink-0">{shortWallet}</span>
      <span className="neon-text-green font-bold w-20 flex-shrink-0">${parseFloat(evt.amountUsdc).toFixed(4)}</span>
      <span className="text-terminal-dim truncate">
        <a href={`https://basescan.org/tx/${evt.txHash}`} target="_blank" rel="noopener noreferrer"
           className="hover:text-neon-cyan transition-colors">
          {evt.txHash.slice(0, 16)}…
        </a>
      </span>
      {evt.xrplTxHash && (
        <span className="badge bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/30">
          XRPL
        </span>
      )}
    </div>
  )
}
