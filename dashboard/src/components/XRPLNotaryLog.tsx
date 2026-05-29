import type { XRPLNotaryEntry } from '../types'

interface Props {
  entries: XRPLNotaryEntry[]
}

export default function XRPLNotaryLog({ entries }: Props) {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold neon-text-green tracking-wider">XRPL NOTARY — GHOST LAYER</h1>
        <p className="text-xs text-terminal-dim mt-0.5">
          On-chain trust records written to XRPL after every Base settlement
        </p>
      </div>

      {/* Info banner */}
      <div className="panel border-neon-green/30 bg-neon-green/5">
        <div className="flex items-start gap-3">
          <span className="text-neon-green text-lg mt-0.5">⚡</span>
          <div className="text-xs leading-relaxed">
            <p className="text-neon-green font-bold mb-1">Agent Credit Bureau Protocol</p>
            <p className="text-terminal-dim">
              Each successful USDC payment on Base triggers an async XRPL Memo transaction.
              The memo encodes <code className="text-neon-cyan">agentEVMAddr | baseTxHash | timestamp</code> on-chain,
              creating a cross-chain reputation trail that any XRPL participant can verify.
            </p>
          </div>
        </div>
      </div>

      {/* Log table */}
      <div className="panel overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-terminal-border">
              <th className="text-left text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Time</th>
              <th className="text-left text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Agent (EVM)</th>
              <th className="text-left text-terminal-dim py-2 pr-4 uppercase tracking-widest font-normal">Base Tx</th>
              <th className="text-left text-terminal-dim py-2 uppercase tracking-widest font-normal">XRPL Tx</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr>
                <td colSpan={4} className="py-8 text-center text-terminal-dim">
                  No notary entries yet
                </td>
              </tr>
            )}
            {entries.map((entry, i) => (
              <NotaryRow key={i} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function NotaryRow({ entry }: { entry: XRPLNotaryEntry }) {
  const time = new Date(entry.timestamp).toLocaleTimeString()
  return (
    <tr className="table-row animate-slide-in">
      <td className="py-2.5 pr-4 text-terminal-dim">{time}</td>
      <td className="py-2.5 pr-4">
        <span className="text-neon-cyan font-mono">
          {entry.agentWallet.slice(0, 8)}…{entry.agentWallet.slice(-4)}
        </span>
      </td>
      <td className="py-2.5 pr-4">
        <a
          href={`https://basescan.org/tx/${entry.baseTxHash}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-terminal-dim hover:text-neon-cyan transition-colors"
        >
          {entry.baseTxHash.slice(0, 12)}…
        </a>
      </td>
      <td className="py-2.5">
        {entry.xrplTxHash ? (
          <a
            href={`https://xrpscan.com/tx/${entry.xrplTxHash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-neon-green hover:underline"
          >
            {entry.xrplTxHash.slice(0, 12)}…
          </a>
        ) : (
          <span className="text-terminal-dim">pending…</span>
        )}
      </td>
    </tr>
  )
}
