import type { AgentStats } from '../types'

interface Props {
  agents: AgentStats[]
}

export default function AgentTracker({ agents }: Props) {
  const sorted = [...agents].sort((a, b) => parseFloat(b.usdcSpent) - parseFloat(a.usdcSpent))

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold neon-text-magenta tracking-wider">AGENT TRACKER</h1>
        <p className="text-xs text-terminal-dim mt-0.5">Per-wallet spend, request volume, and XRPL reputation score</p>
      </div>

      <div className="panel overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-terminal-border">
              <th className="text-left text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Rank</th>
              <th className="text-left text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Agent Wallet</th>
              <th className="text-right text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Requests</th>
              <th className="text-right text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">USDC Spent</th>
              <th className="text-right text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Reputation</th>
              <th className="text-right text-terminal-dim py-2 uppercase tracking-widest font-normal">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 && (
              <tr><td colSpan={6} className="py-8 text-center text-terminal-dim">No agents yet</td></tr>
            )}
            {sorted.map((agent, i) => (
              <AgentRow key={agent.wallet} rank={i + 1} agent={agent} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function AgentRow({ rank, agent }: { rank: number; agent: AgentStats }) {
  const repColor = agent.reputation > 10 ? 'neon-text-green' : agent.reputation > 3 ? 'neon-text-amber' : 'text-terminal-dim'
  const lastSeen = new Date(agent.lastSeen)
  const timeAgo = formatTimeAgo(lastSeen)

  return (
    <tr className="table-row">
      <td className="py-2.5 pr-4">
        <span className={`font-bold ${rank === 1 ? 'neon-text-amber' : rank === 2 ? 'text-terminal-text' : 'text-terminal-dim'}`}>
          #{rank}
        </span>
      </td>
      <td className="py-2.5 pr-4">
        <span className="text-neon-cyan font-mono">
          {agent.wallet.slice(0, 8)}…{agent.wallet.slice(-6)}
        </span>
        <span className="text-terminal-dim ml-2 text-xs">{agent.wallet.slice(0, 6)}</span>
      </td>
      <td className="py-2.5 pr-4 text-right">
        <span className="text-terminal-text">{agent.requests.toLocaleString()}</span>
      </td>
      <td className="py-2.5 pr-4 text-right">
        <span className="neon-text-green font-bold">${parseFloat(agent.usdcSpent).toFixed(4)}</span>
      </td>
      <td className="py-2.5 pr-4 text-right">
        <ReputationBar score={agent.reputation} />
        <span className={`${repColor} ml-2`}>{agent.reputation}</span>
      </td>
      <td className="py-2.5 text-right text-terminal-dim">{timeAgo}</td>
    </tr>
  )
}

function ReputationBar({ score }: { score: number }) {
  const pct = Math.min(100, (score / 50) * 100)
  const color = score > 10 ? '#00FF41' : score > 3 ? '#FFB800' : '#666'
  return (
    <span className="inline-flex items-center">
      <span className="inline-block w-16 h-1.5 bg-terminal-muted rounded-full overflow-hidden">
        <span className="block h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </span>
    </span>
  )
}

function formatTimeAgo(date: Date): string {
  const s = Math.floor((Date.now() - date.getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
