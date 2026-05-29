import { useState } from 'react'
import { useSSE } from './hooks/useSSE'
import Sidebar from './components/Sidebar'
import RevenuePanel from './components/RevenuePanel'
import AgentTracker from './components/AgentTracker'
import XRPLNotaryLog from './components/XRPLNotaryLog'
import Settings from './components/Settings'
import type { Page } from './types'

export default function App() {
  const [page, setPage] = useState<Page>('revenue')
  const { snapshot, feed, notaryLog, connected } = useSSE()

  return (
    <div className="scanlines flex h-screen overflow-hidden bg-terminal-bg">
      <Sidebar page={page} onNavigate={setPage} connected={connected} />
      <main className="flex-1 overflow-y-auto">
        {page === 'revenue'  && <RevenuePanel snapshot={snapshot} feed={feed} />}
        {page === 'agents'   && <AgentTracker agents={snapshot?.agents ?? []} />}
        {page === 'notary'   && <XRPLNotaryLog entries={notaryLog} />}
        {page === 'settings' && <Settings />}
      </main>
    </div>
  )
}
