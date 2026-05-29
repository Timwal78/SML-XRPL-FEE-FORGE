import type { Page } from '../types'

interface Props {
  page: Page
  onNavigate: (p: Page) => void
  connected: boolean
}

const NAV: { id: Page; label: string; icon: string }[] = [
  { id: 'revenue',  label: 'REVENUE',      icon: '$' },
  { id: 'agents',   label: 'AGENTS',       icon: '■' },
  { id: 'notary',   label: 'XRPL NOTARY',  icon: '★' },
  { id: 'settings', label: 'SETTINGS',     icon: '⚙' },
]

export default function Sidebar({ page, onNavigate, connected }: Props) {
  return (
    <aside className="w-52 flex-shrink-0 flex flex-col border-r border-terminal-border bg-terminal-surface">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-terminal-border">
        <div className="text-xs text-terminal-dim tracking-widest mb-1">SML ► FORGE</div>
        <div className="text-neon-cyan font-bold text-sm tracking-widest" style={{textShadow:'0 0 10px #00FFFF'}}>
          x402 GATEWAY
        </div>
      </div>

      {/* Connection status */}
      <div className="px-4 py-2 border-b border-terminal-border">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${connected ? 'bg-neon-green shadow-neon-green animate-pulse' : 'bg-neon-red shadow-neon-red animate-pulse'}`}
          />
          <span className={connected ? 'text-neon-green' : 'text-neon-red'}>
            {connected ? 'LIVE' : 'RECONNECTING'}
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2">
        {NAV.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            className={`nav-item w-full text-left ${page === id ? 'active' : ''}`}
          >
            <span className="text-xs w-4 text-center">{icon}</span>
            <span className="tracking-wider text-xs">{label}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-terminal-border">
        <div className="text-xs text-terminal-dim">BASE × XRPL</div>
        <div className="text-xs text-terminal-dim">USDC — EIP-3009</div>
      </div>
    </aside>
  )
}
