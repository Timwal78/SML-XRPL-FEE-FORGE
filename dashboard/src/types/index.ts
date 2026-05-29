export interface PaymentEvent {
  type: 'payment'
  timestamp: string
  payer: string
  amountUsdc: string
  txHash: string
  resource: string
  xrplTxHash?: string
}

export interface AgentStats {
  wallet: string
  requests: number
  usdcSpent: string
  reputation: number
  lastSeen: string
}

export interface XRPLNotaryEntry {
  timestamp: string
  agentWallet: string
  baseTxHash: string
  xrplTxHash: string
  memo: string
}

export interface StatsSnapshot {
  totalUsdc: string
  totalTx: number
  txPerHour: number
  activeAgents: number
  agents: AgentStats[]
  recentNotary: XRPLNotaryEntry[]
}

export type SSEMessage =
  | { type: 'snapshot'; data: StatsSnapshot }
  | { type: 'payment'; data: PaymentEvent }
  | { type: 'notary'; data: XRPLNotaryEntry }

export type Page = 'revenue' | 'agents' | 'notary' | 'settings'
