import { useEffect, useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import PriceChart from './PriceChart.jsx'
import FundSummary from './FundSummary.jsx'
import './Dashboard.css'
import { CATEGORY_ORDER, CATEGORY_META } from './categoryMeta.js'

const API = 'http://localhost:8000'
const WS_URL = 'ws://localhost:8000/ws/prices'

function groupByCategory(assets) {
  const groups = {}
  for (const asset of assets) {
    if (!groups[asset.category]) groups[asset.category] = []
    groups[asset.category].push(asset)
  }
  return groups
}

// Renders a string with **bold** markers into React elements
function renderInline(text) {
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part
  )
}

// Splits rationale into an optional heading line + body paragraphs
function parseRationale(text) {
  const lines = text.trim().split('\n').map(l => l.trim()).filter(Boolean)
  let heading = null
  let bodyLines = lines

  // If the first line is entirely wrapped in ** it's a heading
  if (/^\*\*.+\*\*$/.test(lines[0])) {
    heading = lines[0].replace(/^\*\*|\*\*$/g, '')
    bodyLines = lines.slice(1)
  }

  return { heading, body: bodyLines.join(' ') }
}

/**
 * Theme + financial from API, or derived from legacy combined `rationale`
 * (double newline, or pivot phrases like "From a financial perspective").
 */
function deriveThemeAndFinancial(asset) {
  const apiTheme = (asset.theme_rationale || '').trim()
  const apiFin = (asset.financial_rationale || '').trim()
  if (apiTheme || apiFin) {
    return { theme: apiTheme, financial: apiFin }
  }

  const raw = (asset.rationale || '').trim()
  if (!raw) return null

  const paras = raw.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean)
  if (paras.length >= 2) {
    return { theme: paras[0], financial: paras.slice(1).join('\n\n') }
  }

  const pivot = raw.match(
    /^([\s\S]+?)(\s+(?:From a financial perspective|Beyond the numbers|Financially,|On the financial side|From a numbers perspective|The numbers (?:are|tell|show))[\s\S]*)$/i
  )
  if (pivot) {
    return { theme: pivot[1].trim(), financial: pivot[2].trim() }
  }

  return null
}

function RationaleSplitSections({ theme, financial }) {
  const showTheme = Boolean(theme)
  const showFin = Boolean(financial)
  if (!showTheme && !showFin) return null

  return (
    <div className="asset-rationale asset-rationale-split">
      {showTheme && (
        <div className="asset-rationale-block asset-rationale-themes">
          <span className="asset-rationale-label">Why it fits your interests</span>
          <p className="asset-rationale-text">{renderInline(theme)}</p>
        </div>
      )}
      {showTheme && showFin && <hr className="asset-rationale-divider" aria-hidden="true" />}
      {showFin && (
        <div className="asset-rationale-block asset-rationale-financial">
          <span className="asset-rationale-label">Financial rationale</span>
          <p className="asset-rationale-text">{renderInline(financial)}</p>
        </div>
      )}
    </div>
  )
}

function AssetCard({ asset, livePrice }) {
  const meta = CATEGORY_META[asset.category] || { emoji: '📈', color: '#7c3aed' }
  const derived = deriveThemeAndFinancial(asset)
  const { heading, body } =
    !derived && asset.rationale ? parseRationale(asset.rationale) : {}

  return (
    <div className="asset-card">
      <div className="asset-card-header">
        <div className="asset-ticker-row">
          <div className="asset-ticker-group">
            <span className="asset-ticker">{asset.ticker}</span>
            {asset.name && asset.name !== asset.ticker && (
              <span className="asset-company-name">{asset.name}</span>
            )}
          </div>
          {livePrice != null && (
            <span className="asset-live-price">${livePrice.toFixed(2)}</span>
          )}
        </div>
        <span className="asset-category-badge" style={{ background: `${meta.color}22`, color: meta.color }}>
          {meta.emoji} {asset.category}
        </span>
      </div>
      {derived ? (
        <RationaleSplitSections theme={derived.theme} financial={derived.financial} />
      ) : (
        asset.rationale && (
          <div className="asset-rationale">
            {heading && <p className="asset-rationale-heading">{heading}</p>}
            {body && <p className="asset-rationale-body">{renderInline(body)}</p>}
          </div>
        )
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
  const navigate = useNavigate()
  const { token, authHeader, logout } = useAuth()
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [livePrices, setLivePrices] = useState({})
  const [wsStatus, setWsStatus] = useState('connecting')
  const [selectedTicker, setSelectedTicker] = useState(null)
  const priceHistoryRef = useRef({})       // live ticks accumulated per ticker
  const seedBarsRef = useRef({})           // historical bars fetched from backend
  const [priceHistory, setPriceHistory] = useState([])
  const [barsLoading, setBarsLoading] = useState(false)
  const [prevClose, setPrevClose] = useState({})
  const [expectedReturn, setExpectedReturn] = useState({})

  // Fetch portfolio on mount (JWT required), then seed last close prices
  useEffect(() => {
    async function fetchPortfolio() {
      try {
        const res = await fetch(`${API}/users/me/portfolios/`, { headers: { ...authHeader } })
        if (res.status === 401) {
          logout()
          navigate('/login', { replace: true })
          return
        }
        if (!res.ok) throw new Error(`Server error: ${res.status}`)
        const portfolios = await res.json()
        if (portfolios.length === 0) throw new Error('No portfolio found. Complete onboarding first.')
        const latest = portfolios[portfolios.length - 1]
        setPortfolio(latest)

        // Pre-fill with last close prices so cards always show something
        const tickers = latest.assets.map((a) => a.ticker).join(',')
        if (tickers) {
          const priceRes = await fetch(`${API}/api/last-prices?tickers=${tickers}`)
          if (priceRes.ok) {
            const prices = await priceRes.json()
            setLivePrices(prices)
          }
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    if (token) fetchPortfolio()
  }, [token, authHeader, logout, navigate])

  // Fetch previous-close and expected-return for all portfolio tickers
  useEffect(() => {
    if (!portfolio || portfolio.assets.length === 0) return
    const tickers = portfolio.assets.map((a) => a.ticker).join(',')
    const encoded = encodeURIComponent(tickers)

    fetch(`${API}/api/prev-close?tickers=${encoded}`)
      .then((r) => r.ok ? r.json() : {})
      .then((data) => setPrevClose(data))
      .catch(() => {})

    fetch(`${API}/api/expected-return?tickers=${encoded}`)
      .then((r) => r.ok ? r.json() : {})
      .then((data) => setExpectedReturn(data))
      .catch(() => {})
  }, [portfolio])

  // WebSocket for live prices
  useEffect(() => {
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => setWsStatus('connected')
    ws.onclose = () => setWsStatus('disconnected')
    ws.onerror = () => setWsStatus('error')

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.ticker && data.price != null) {
          setLivePrices((prev) => ({ ...prev, [data.ticker]: data.price }))

          const timestamp = Math.floor(Date.now() / 1000)
          const ticker = data.ticker
          if (!priceHistoryRef.current[ticker]) {
            priceHistoryRef.current[ticker] = []
          }
          const hist = priceHistoryRef.current[ticker]
          if (hist.length === 0 || hist[hist.length - 1].time !== timestamp) {
            hist.push({ time: timestamp, value: data.price })
          } else {
            hist[hist.length - 1].value = data.price
          }

          setSelectedTicker((cur) => {
            if (cur === ticker) {
              const seed = seedBarsRef.current[ticker] || []
              const live = priceHistoryRef.current[ticker] || []
              const liveStart = live[0]?.time ?? Infinity
              const filtered = seed.filter((p) => p.time < liveStart)
              setPriceHistory([...filtered, ...live])
            }
            return cur
          })
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
        <DashboardNav onLogout={logout} />
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
        <DashboardNav onLogout={logout} />
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
  const allTickers = portfolio.assets.map((a) => a.ticker)

  function mergedHistory(ticker) {
    const seed = seedBarsRef.current[ticker] || []
    const live = priceHistoryRef.current[ticker] || []
    if (live.length === 0) return seed

    // Drop seed points that overlap with live data to avoid duplicate timestamps
    const liveStart = live[0].time
    const filtered = seed.filter((p) => p.time < liveStart)
    return [...filtered, ...live]
  }

  async function handleSelectTicker(ticker) {
    setSelectedTicker(ticker)
    setBarsLoading(true)

    // Show whatever live data we already have immediately
    setPriceHistory(mergedHistory(ticker))

    // Fetch historical bars if not yet cached
    if (!seedBarsRef.current[ticker]) {
      try {
        const res = await fetch(`${API}/api/bars/${ticker}`)
        if (res.ok) {
          const json = await res.json()
          seedBarsRef.current[ticker] = json.bars || []
        }
      } catch {
        // silently fall through — chart will just show live data
      }
    }

    setBarsLoading(false)
    // Re-merge now that seed bars are loaded
    setPriceHistory(mergedHistory(ticker))
  }

  return (
    <div className="dashboard-page">
      <DashboardNav onLogout={logout} />

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

        <FundSummary
          assets={portfolio.assets}
          prevClose={prevClose}
          expectedReturn={expectedReturn}
          livePrices={livePrices}
          seedBarsRef={seedBarsRef}
        />

        <div className="chart-section">
          <div className="chart-section-header">
            <h2 className="chart-section-title">Live Price Chart</h2>
            <div className="ticker-selector">
              {allTickers.map((ticker) => {
                const asset = portfolio.assets.find((a) => a.ticker === ticker)
                const meta = CATEGORY_META[asset?.category] || { color: '#7c3aed' }
                return (
                  <button
                    key={ticker}
                    className={`ticker-btn${selectedTicker === ticker ? ' ticker-btn--active' : ''}`}
                    style={selectedTicker === ticker ? { borderColor: meta.color, color: meta.color, background: `${meta.color}18` } : {}}
                    onClick={() => handleSelectTicker(ticker)}
                  >
                    {ticker}
                  </button>
                )
              })}
            </div>
          </div>

          {selectedTicker ? (
            <PriceChart
              key={selectedTicker}
              ticker={selectedTicker}
              priceHistory={priceHistory}
              loading={barsLoading}
              color={CATEGORY_META[portfolio.assets.find((a) => a.ticker === selectedTicker)?.category]?.color ?? '#3b82f6'}
            />
          ) : (
            <div className="chart-placeholder">
              <span>Select a ticker above to view its price chart</span>
            </div>
          )}
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

function DashboardNav({ onLogout }) {
  return (
    <nav className="dashboard-nav">
      <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
        Theme<span>Trader</span>
      </Link>
      <div className="dashboard-nav-right">
        <Link to="/onboarding" className="btn-ghost-sm">New Fund</Link>
        <button type="button" className="btn-ghost-sm" onClick={onLogout}>
          Log out
        </button>
      </div>
    </nav>
  )
}
