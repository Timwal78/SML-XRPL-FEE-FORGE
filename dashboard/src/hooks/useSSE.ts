import { useEffect, useRef, useState, useCallback } from 'react'
import type { SSEMessage, StatsSnapshot, PaymentEvent, XRPLNotaryEntry } from '../types'

// VITE_GATEWAY_URL is set at build time:
//   - Local dev: empty string (Vite proxies /api/ to localhost:8080)
//   - Render / production: https://x402-gateway.onrender.com
const GATEWAY_BASE = (import.meta.env.VITE_GATEWAY_URL as string) ?? ''
const SSE_URL = `${GATEWAY_BASE}/api/stream`

const MAX_FEED_ITEMS = 50

export function useSSE() {
  const [snapshot, setSnapshot] = useState<StatsSnapshot | null>(null)
  const [feed, setFeed] = useState<PaymentEvent[]>([])
  const [notaryLog, setNotaryLog] = useState<XRPLNotaryEntry[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectDelay = useRef(1000)

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
    }

    const es = new EventSource(SSE_URL)
    esRef.current = es

    es.onopen = () => {
      setConnected(true)
      reconnectDelay.current = 1000
    }

    es.onmessage = (e: MessageEvent) => {
      try {
        const msg: SSEMessage = JSON.parse(e.data as string)
        if (msg.type === 'snapshot') {
          setSnapshot(msg.data)
          if (msg.data.recentNotary) {
            setNotaryLog(msg.data.recentNotary)
          }
        } else if (msg.type === 'payment') {
          setFeed(prev => [msg.data, ...prev].slice(0, MAX_FEED_ITEMS))
          setSnapshot(prev => {
            if (!prev) return prev
            return {
              ...prev,
              totalTx: prev.totalTx + 1,
              totalUsdc: addUsdc(prev.totalUsdc, msg.data.amountUsdc),
              txPerHour: prev.txPerHour + 1,
            }
          })
        } else if (msg.type === 'notary') {
          setNotaryLog(prev => [msg.data, ...prev].slice(0, MAX_FEED_ITEMS))
        }
      } catch { /* malformed SSE frame — skip */ }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
      esRef.current = null
      const delay = Math.min(reconnectDelay.current * 2, 30000)
      reconnectDelay.current = delay
      reconnectTimer.current = setTimeout(connect, delay)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      esRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [connect])

  return { snapshot, feed, notaryLog, connected }
}

function addUsdc(a: string, b: string): string {
  return (parseFloat(a || '0') + parseFloat(b || '0')).toFixed(6)
}
