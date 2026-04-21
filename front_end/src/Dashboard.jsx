import { useEffect, useState, useRef, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import PriceChart from './PriceChart.jsx'
import FundSummary from './FundSummary.jsx'
import './Dashboard.css'
import { CATEGORY_ORDER, CATEGORY_META } from './categoryMeta.js'
import { API_URL, WS_URL } from './config.js'

const API = API_URL

const INDEX_SYMBOLS = { dji: '^DJI', spx: '^GSPC', ixic: '^IXIC' }

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
  if (typeof text !== 'string') return { heading: null, body: '' }
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
          {livePrice != null && Number.isFinite(Number(livePrice)) && (
            <span className="asset-live-price">${Number(livePrice).toFixed(2)}</span>
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
  const { token, logout } = useAuth()
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
  const [compareIdx, setCompareIdx] = useState({ dji: false, spx: false, ixic: false })
  const [indexBars, setIndexBars] = useState({})
  const indexCacheRef = useRef({})

  // Fetch portfolio on mount (JWT required), then seed last close prices.
  // Depend on `token` only — `authHeader` is a new object every context update and would retrigger this effect endlessly.
  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }

    let cancelled = false
    async function fetchPortfolio() {
      try {
        const res = await fetch(`${API}/users/me/portfolios/`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.status === 401) {
          logout()
          navigate('/login', { replace: true })
          return
        }
        if (!res.ok) throw new Error(`Server error: ${res.status}`)
        const portfolios = await res.json()
        if (portfolios.length === 0) throw new Error('No portfolio found. Complete onboarding first.')
        const latest = portfolios[portfolios.length - 1]
        const assetList = Array.isArray(latest.assets) ? latest.assets : []
        if (cancelled) return
        setPortfolio({ ...latest, assets: assetList })

        const tickers = assetList.map((a) => a.ticker).join(',')
        if (tickers) {
          const priceRes = await fetch(`${API}/api/last-prices?tickers=${tickers}`)
          if (priceRes.ok) {
            const prices = await priceRes.json()
            if (!cancelled) setLivePrices(prices)
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message || String(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPortfolio()
    return () => {
      cancelled = true
    }
  }, [token, logout, navigate])

  // Fetch previous-close and expected-return for all portfolio tickers
  useEffect(() => {
    const pa = portfolio?.assets
    if (!portfolio || !Array.isArray(pa) || pa.length === 0) return
    const tickers = pa.map((a) => a.ticker).join(',')
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

  // Intraday bars for benchmark indexes (cached) when compare toggles are on
  useEffect(() => {
    const need = []
    if (compareIdx.dji) need.push(INDEX_SYMBOLS.dji)
    if (compareIdx.spx) need.push(INDEX_SYMBOLS.spx)
    if (compareIdx.ixic) need.push(INDEX_SYMBOLS.ixic)
    if (need.length === 0) return

    let cancelled = false
    ;(async () => {
      for (const sym of need) {
        if (indexCacheRef.current[sym]?.length) {
          setIndexBars((prev) => ({ ...prev, [sym]: indexCacheRef.current[sym] }))
          continue
        }
        try {
          const res = await fetch(`${API}/api/bars/${encodeURIComponent(sym)}`)
          if (!res.ok) continue
          const j = await res.json()
          const bars = j.bars || []
          if (cancelled) return
          indexCacheRef.current[sym] = bars
          setIndexBars((prev) => ({ ...prev, [sym]: bars }))
        } catch {
          // ignore — chart still shows the primary series
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [compareIdx.dji, compareIdx.spx, compareIdx.ixic])

  // WebSocket for live prices
  useEffect(() => {
    if (!WS_URL) {
      setWsStatus('disconnected')
      return undefined
    }

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

  const overlayPrices = useMemo(
    () => ({
      dji: indexBars[INDEX_SYMBOLS.dji],
      spx: indexBars[INDEX_SYMBOLS.spx],
      ixic: indexBars[INDEX_SYMBOLS.ixic],
    }),
    [indexBars]
  )

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

  if (!portfolio) {
    return (
      <div className="dashboard-page">
        <DashboardNav onLogout={logout} />
        <div className="dashboard-error">
          <h2>No portfolio data</h2>
          <p>Try completing onboarding again.</p>
          <Link to="/onboarding" className="btn-primary">Start Over</Link>
        </div>
      </div>
    )
  }

  const assets = Array.isArray(portfolio.assets) ? portfolio.assets : []
  const grouped = groupByCategory(assets)
  const orderedCategories = [
    ...CATEGORY_ORDER.filter((c) => grouped[c]),
    ...Object.keys(grouped).filter((c) => !CATEGORY_ORDER.includes(c)),
  ]

  const totalAssets = assets.length
  const allTickers = assets.map((a) => a.ticker)

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
          assets={assets}
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
                const asset = assets.find((a) => a.ticker === ticker)
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

          <div className="chart-compare-bar" aria-label="Benchmark overlays">
            <span className="chart-compare-label">Compare vs</span>
            <label className="chart-compare-item">
              <input
                type="checkbox"
                checked={compareIdx.dji}
                onChange={(e) => setCompareIdx((c) => ({ ...c, dji: e.target.checked }))}
              />
              <span className="chart-compare-swatch" style={{ background: '#e2e8f0' }} />
              DJI
            </label>
            <label className="chart-compare-item">
              <input
                type="checkbox"
                checked={compareIdx.spx}
                onChange={(e) => setCompareIdx((c) => ({ ...c, spx: e.target.checked }))}
              />
              <span className="chart-compare-swatch" style={{ background: '#38bdf8' }} />
              SPX
            </label>
            <label className="chart-compare-item">
              <input
                type="checkbox"
                checked={compareIdx.ixic}
                onChange={(e) => setCompareIdx((c) => ({ ...c, ixic: e.target.checked }))}
              />
              <span className="chart-compare-swatch" style={{ background: '#f472b6' }} />
              IXIC
            </label>
            <span className="chart-compare-hint">Same session (1m). Normalized % from first bar.</span>
          </div>

          {selectedTicker ? (
            <PriceChart
              key={selectedTicker}
              ticker={selectedTicker}
              priceHistory={priceHistory}
              loading={barsLoading}
              color={CATEGORY_META[assets.find((a) => a.ticker === selectedTicker)?.category]?.color ?? '#3b82f6'}
              overlayEnabled={compareIdx}
              overlayPrices={overlayPrices}
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
