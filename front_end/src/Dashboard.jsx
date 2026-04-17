import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import './Dashboard.css'

const API = 'http://localhost:8000'
const WS_URL = 'ws://localhost:8000/ws/prices'

const CATEGORY_ORDER = ['ETF', 'Blue Chip', 'Rising Star', 'IPO']

const CATEGORY_META = {
  'ETF': { emoji: '📊', color: '#3b82f6' },
  'Blue Chip': { emoji: '💎', color: '#10b981' },
  'Rising Star': { emoji: '🚀', color: '#f59e0b' },
  'IPO': { emoji: '✨', color: '#ec4899' },
}

function groupByCategory(assets) {
  const groups = {}
  for (const asset of assets) {
    if (!groups[asset.category]) groups[asset.category] = []
    groups[asset.category].push(asset)
  }
  return groups
}

function AssetCard({ asset, livePrice }) {
  const meta = CATEGORY_META[asset.category] || { emoji: '📈', color: '#7c3aed' }

  return (
    <div className="asset-card">
      <div className="asset-card-header">
        <div className="asset-ticker-row">
          <span className="asset-ticker">{asset.ticker}</span>
          {livePrice != null && (
            <span className="asset-live-price">${livePrice.toFixed(2)}</span>
          )}
        </div>
        <span className="asset-category-badge" style={{ background: `${meta.color}22`, color: meta.color }}>
          {meta.emoji} {asset.category}
        </span>
      </div>
      {asset.rationale && (
        <p className="asset-rationale">{asset.rationale}</p>
      )}
    </div>
  )
}

function CategorySection({ category, assets, livePrices }) {
  const meta = CATEGORY_META[category] || { emoji: '📈', color: '#7c3aed' }
  return (
    <div className="category-section">
      <div className="category-heading">
        <span className="category-emoji">{meta.emoji}</span>
        <h2>{category}</h2>
        <span className="category-count">{assets.length} asset{assets.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="assets-grid">
        {assets.map((asset) => (
          <AssetCard
            key={asset.id}
            asset={asset}
            livePrice={livePrices[asset.ticker] ?? null}
          />
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { userId } = useParams()
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [livePrices, setLivePrices] = useState({})
  const [wsStatus, setWsStatus] = useState('connecting')
  const wsRef = useRef(null)

  // Fetch portfolio on mount
  useEffect(() => {
    async function fetchPortfolio() {
      try {
        const res = await fetch(`${API}/users/${userId}/portfolios/`)
        if (!res.ok) throw new Error(`Server error: ${res.status}`)
        const portfolios = await res.json()
        if (portfolios.length === 0) throw new Error('No portfolio found for this user.')
        // Show the most recently created portfolio (last in list)
        setPortfolio(portfolios[portfolios.length - 1])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchPortfolio()
  }, [userId])

  // WebSocket for live prices
  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setWsStatus('connected')
    ws.onclose = () => setWsStatus('disconnected')
    ws.onerror = () => setWsStatus('error')

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.ticker && data.price != null) {
          setLivePrices((prev) => ({ ...prev, [data.ticker]: data.price }))
        }
      } catch {
        // ignore malformed messages
      }
    }

    return () => ws.close()
  }, [])

  if (loading) {
    return (
      <div className="dashboard-page">
        <DashboardNav />
        <div className="dashboard-loading">
          <div className="spinner" />
          <p>Loading your portfolio…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard-page">
        <DashboardNav />
        <div className="dashboard-error">
          <h2>Something went wrong</h2>
          <p>{error}</p>
          <Link to="/onboarding" className="btn-primary">Start Over</Link>
        </div>
      </div>
    )
  }

  const grouped = groupByCategory(portfolio.assets)
  const orderedCategories = [
    ...CATEGORY_ORDER.filter((c) => grouped[c]),
    ...Object.keys(grouped).filter((c) => !CATEGORY_ORDER.includes(c)),
  ]

  const totalAssets = portfolio.assets.length

  return (
    <div className="dashboard-page">
      <DashboardNav />

      <div className="dashboard-inner">
        <div className="dashboard-hero">
          <div>
            <span className="section-tag">Your Fund</span>
            <h1 className="dashboard-title">{portfolio.name}</h1>
            <p className="dashboard-sub">
              {totalAssets} assets across {orderedCategories.length} categories
            </p>
          </div>
          <div className="ws-indicator">
            <span className={`ws-dot ws-dot--${wsStatus}`} />
            <span className="ws-label">
              {wsStatus === 'connected' ? 'Live prices' : wsStatus === 'connecting' ? 'Connecting…' : 'Prices offline'}
            </span>
          </div>
        </div>

        {orderedCategories.map((cat) => (
          <CategorySection
            key={cat}
            category={cat}
            assets={grouped[cat]}
            livePrices={livePrices}
          />
        ))}
      </div>
    </div>
  )
}

function DashboardNav() {
  return (
    <nav className="dashboard-nav">
      <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
        Theme<span>Trader</span>
      </Link>
      <div className="dashboard-nav-right">
        <Link to="/onboarding" className="btn-ghost-sm">New Fund</Link>
      </div>
    </nav>
  )
}
