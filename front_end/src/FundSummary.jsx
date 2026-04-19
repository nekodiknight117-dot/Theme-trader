import { useEffect, useMemo, useState } from 'react'

const API = 'http://localhost:8000'

const CATEGORY_META = {
  ETF: { emoji: '📊', color: '#3b82f6' },
  'Blue Chip': { emoji: '💎', color: '#10b981' },
  'Rising Star': { emoji: '🚀', color: '#f59e0b' },
  IPO: { emoji: '✨', color: '#ec4899' },
}

/** @type {{ id: string, label: string }[]} */
export const PERFORMANCE_PERIODS = [
  { id: 'ytd', label: 'YTD' },
  { id: '3m', label: '3M' },
  { id: '6m', label: '6M' },
  { id: '1y', label: '1Y' },
  { id: '5y', label: '5Y' },
  { id: '10y', label: '10Y' },
  { id: 'max', label: 'Max' },
]

function pct(value) {
  const v = Number(value)
  if (!Number.isFinite(v)) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function fmtUsd(value) {
  const v = Number(value)
  if (value == null || !Number.isFinite(v)) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}$${Math.abs(v).toFixed(2)}`
}

function fmtVolume(n) {
  const v = Number(n)
  if (n == null || !Number.isFinite(v)) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`
  return String(Math.round(v))
}

function fmtMarketCap(n) {
  const v = Number(n)
  if (n == null || !Number.isFinite(v)) return '—'
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  return `$${Math.round(v)}`
}

function ReturnBadge({ value }) {
  const v = Number(value)
  if (value == null || !Number.isFinite(v)) {
    return <span className="return-badge return-badge--neutral">—</span>
  }
  const cls = v >= 0 ? 'return-badge--pos' : 'return-badge--neg'
  return <span className={`return-badge ${cls}`}>{pct(v)}</span>
}

function PerfPair({ pctVal, dollarShare }) {
  const pv = pctVal == null ? null : Number(pctVal)
  const ds = dollarShare == null ? null : Number(dollarShare)
  const hasPv = pv != null && Number.isFinite(pv)
  const hasDs = ds != null && Number.isFinite(ds)
  if (!hasPv && !hasDs) {
    return (
      <span className="perf-pair">
        <span className="return-badge return-badge--neutral">—</span>
      </span>
    )
  }
  const cls = hasPv ? (pv >= 0 ? 'return-badge--pos' : 'return-badge--neg') : 'return-badge--neutral'
  const pctStr = hasPv ? pct(pv) : '—'
  const usdStr = hasDs ? fmtUsd(ds) : '—'
  return (
    <span className="perf-pair">
      <span className={`return-badge ${cls}`}>{pctStr}</span>
      <span className="perf-dollar">{usdStr}</span>
      <span className="perf-dollar-hint">/ sh</span>
    </span>
  )
}

export default function FundSummary({ assets: assetsIn, prevClose, expectedReturn = {}, livePrices, seedBarsRef }) {
  const assets = Array.isArray(assetsIn) ? assetsIn : []
  const n = assets.length
  const [period, setPeriod] = useState('1y')
  const [periodPerf, setPeriodPerf] = useState({})
  const [fundamentals, setFundamentals] = useState({})

  const tickerKey = useMemo(() => assets.map((a) => a.ticker).sort().join(','), [assets])

  useEffect(() => {
    if (!tickerKey) return
    const enc = encodeURIComponent(tickerKey)
    fetch(`${API}/api/period-performance?tickers=${enc}&period=${encodeURIComponent(period)}`)
      .then((r) => (r.ok ? r.json() : {}))
      .then(setPeriodPerf)
      .catch(() => setPeriodPerf({}))

    fetch(`${API}/api/fundamentals?tickers=${enc}`)
      .then((r) => (r.ok ? r.json() : {}))
      .then(setFundamentals)
      .catch(() => setFundamentals({}))
  }, [tickerKey, period])

  if (n === 0) return null

  function currentPrice(ticker) {
    if (livePrices[ticker] != null) {
      const v = Number(livePrices[ticker])
      return Number.isFinite(v) ? v : null
    }
    const bars = seedBarsRef?.current?.[ticker]
    if (bars && bars.length > 0) {
      const v = Number(bars[bars.length - 1].value)
      return Number.isFinite(v) ? v : null
    }
    return null
  }

  function assetReturn(ticker) {
    const cur = currentPrice(ticker)
    const pc = Number(prevClose[ticker])
    if (cur == null || !Number.isFinite(pc) || pc === 0) return null
    return ((cur - pc) / pc) * 100
  }

  /**
   * Per-asset beta weights supplied by the backend (sum to 1.0).
   * Fall back to equal weight if an asset has no weight field.
   */
  const assetWeights = useMemo(() => {
    const hasBetaWeight = assets.every((a) => typeof a.weight === 'number')
    if (hasBetaWeight) {
      // Re-normalise in case of floating-point drift
      const total = assets.reduce((s, a) => s + a.weight, 0)
      return Object.fromEntries(assets.map((a) => [a.ticker, total > 0 ? a.weight / total : 1 / n]))
    }
    return Object.fromEntries(assets.map((a) => [a.ticker, 1 / n]))
  }, [assets, n])

  const isBetaWeighted = assets.every((a) => typeof a.weight === 'number')

  // Weighted today's return
  const _retPairs = assets.map((a) => ({ w: assetWeights[a.ticker], r: assetReturn(a.ticker) })).filter(({ r }) => r != null)
  const _retWSum = _retPairs.reduce((s, { w }) => s + w, 0)
  const fundReturn = _retPairs.length > 0 && _retWSum > 0
    ? _retPairs.reduce((s, { w, r }) => s + (w / _retWSum) * r, 0)
    : null

  // Weighted expected return
  const _expPairs = assets.map((a) => ({ w: assetWeights[a.ticker], r: Number(expectedReturn[a.ticker]) })).filter(({ r }) => Number.isFinite(r))
  const _expWSum = _expPairs.reduce((s, { w }) => s + w, 0)
  const fundExpectedReturn = _expPairs.length > 0 && _expWSum > 0
    ? _expPairs.reduce((s, { w, r }) => s + (w / _expWSum) * r, 0)
    : null

  // Weighted period return
  const _pPairs = assets.map((a) => ({ w: assetWeights[a.ticker], x: Number(periodPerf[a.ticker]?.pct) })).filter(({ x }) => Number.isFinite(x))
  const _pWSum = _pPairs.reduce((s, { w }) => s + w, 0)
  const fundPeriodPct = _pPairs.length > 0 && _pWSum > 0
    ? _pPairs.reduce((s, { w, x }) => s + (w / _pWSum) * x, 0)
    : null

  /** Beta-weighted portfolio P/L on a $10,000 notional. */
  const notionalTotal = 10000
  const fundPeriodDollar =
    fundPeriodPct != null ? (notionalTotal * fundPeriodPct) / 100 : null

  // Category weights = sum of individual asset weights per category
  const catWeights = {}
  for (const a of assets) {
    catWeights[a.category] = (catWeights[a.category] || 0) + (assetWeights[a.ticker] || 0)
  }
  const catOrder = Object.keys(catWeights).sort((a, b) => catWeights[b] - catWeights[a])

  const periodLabel = PERFORMANCE_PERIODS.find((p) => p.id === period)?.label ?? period.toUpperCase()

  return (
    <div className="fund-summary">
      <div className="fund-summary-top">
        <div className="fund-kpi">
          <span className="fund-kpi-label">Today&apos;s Return</span>
          <ReturnBadge value={fundReturn} />
        </div>
        <div className="fund-kpi fund-kpi--highlight">
          <span className="fund-kpi-label">Expected Return (1Y)</span>
          {fundExpectedReturn != null ? (
            <ReturnBadge value={fundExpectedReturn} />
          ) : (
            <span className="fund-kpi-loading">Calculating…</span>
          )}
        </div>
        <div className="fund-kpi fund-kpi--highlight fund-kpi--period">
          <span className="fund-kpi-label">Period ({periodLabel})</span>
          {fundPeriodPct != null ? (
            <div className="fund-period-stack">
              <ReturnBadge value={fundPeriodPct} />
              <span
                className={`fund-dollar-pl ${
                  fundPeriodDollar != null && fundPeriodDollar >= 0 ? 'fund-dollar-pl--pos' : 'fund-dollar-pl--neg'
                }`}
              >
                {fundPeriodDollar != null ? fmtUsd(fundPeriodDollar) : '—'}
                <span className="fund-dollar-pl-hint"> on $10k</span>
              </span>
            </div>
          ) : (
            <span className="fund-kpi-loading">—</span>
          )}
        </div>
        <div className="fund-kpi">
          <span className="fund-kpi-label">Assets</span>
          <span className="fund-kpi-value">{n}</span>
        </div>
        <div className="fund-kpi">
          <span className="fund-kpi-label">Weighting</span>
          <span className="fund-kpi-value">{isBetaWeighted ? 'Beta-weighted' : `Equal (${(100 / n).toFixed(1)}% each)`}</span>
        </div>
      </div>

      <div className="period-selector-row">
        <span className="period-selector-label">Performance window</span>
        <div className="period-selector" role="tablist" aria-label="Performance time window">
          {PERFORMANCE_PERIODS.map((p) => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={period === p.id}
              className={`period-pill${period === p.id ? ' period-pill--active' : ''}`}
              onClick={() => setPeriod(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <span className="period-footnote">Daily closes (yfinance). Shown next to expected return in the table.</span>
      </div>

      <div className="alloc-section">
        <span className="alloc-label">Allocation by Category</span>
        <div className="alloc-bar">
          {catOrder.map((cat) => {
            const weight = (catWeights[cat] || 0) * 100
            const meta = CATEGORY_META[cat] || { color: '#7c3aed' }
            return (
              <div
                key={cat}
                className="alloc-bar-segment"
                style={{ width: `${weight}%`, background: meta.color }}
                title={`${cat}: ${weight.toFixed(1)}%`}
              />
            )
          })}
        </div>
        <div className="alloc-legend">
          {catOrder.map((cat) => {
            const weight = (catWeights[cat] || 0) * 100
            const meta = CATEGORY_META[cat] || { emoji: '📈', color: '#7c3aed' }
            return (
              <div key={cat} className="alloc-legend-item">
                <span className="alloc-dot" style={{ background: meta.color }} />
                <span className="alloc-legend-name">
                  {meta.emoji} {cat}
                </span>
                <span className="alloc-legend-pct">{weight.toFixed(1)}%</span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="asset-returns">
        <span className="alloc-label">Individual Returns</span>
        <div className="asset-returns-table asset-returns-table--wide">
          <div className="asset-returns-header">
            <span>Ticker</span>
            <span>Price</span>
            <span>Prev Close</span>
            <span>Today</span>
            <span>Expected (1Y)</span>
            <span>
              Period ({periodLabel})
              <span className="header-sub"> % · $/sh</span>
            </span>
            <span>Vol</span>
            <span>Mkt cap</span>
            <span>Div %</span>
            <span>Beta</span>
            <span>Weight</span>
            <span>52w range</span>
          </div>
          {assets.map((a) => {
            const ret = assetReturn(a.ticker)
            const exp = expectedReturn[a.ticker] ?? null
            const cur = currentPrice(a.ticker)
            const pc = prevClose[a.ticker]
            const meta = CATEGORY_META[a.category] || { color: '#7c3aed' }
            const pp = periodPerf[a.ticker]
            const f = fundamentals[a.ticker] || {}
            const hi = Number(f.week_52_high)
            const lo = Number(f.week_52_low)
            const range52 =
              Number.isFinite(hi) && Number.isFinite(lo) ? `${hi.toFixed(0)} / ${lo.toFixed(0)}` : '—'
            return (
              <div key={a.ticker} className="asset-return-row">
                <span className="asset-return-ticker" style={{ color: meta.color }}>
                  {a.ticker}
                </span>
                <span className="asset-return-price">
                  {cur != null ? `$${Number(cur).toFixed(2)}` : '—'}
                </span>
                <span className="asset-return-prev">
                  {pc != null && Number.isFinite(Number(pc)) ? `$${Number(pc).toFixed(2)}` : '—'}
                </span>
                <ReturnBadge value={ret} />
                <ReturnBadge value={exp} />
                <PerfPair pctVal={pp?.pct ?? null} dollarShare={pp?.dollar_per_share ?? null} />
                <span className="asset-metric">{fmtVolume(f.volume)}</span>
                <span className="asset-metric">{fmtMarketCap(f.market_cap)}</span>
                <span className="asset-metric">
                  {Number.isFinite(Number(f.dividend_yield_pct))
                    ? `${Number(f.dividend_yield_pct).toFixed(2)}%`
                    : '—'}
                </span>
                <span className="asset-metric">
                  {Number.isFinite(Number(f.beta)) ? Number(f.beta).toFixed(2) : (Number.isFinite(a.beta) ? Number(a.beta).toFixed(2) : '—')}
                </span>
                <span className="asset-metric">
                  {Number.isFinite(assetWeights[a.ticker]) ? `${(assetWeights[a.ticker] * 100).toFixed(1)}%` : '—'}
                </span>
                <span className="asset-metric asset-metric--tight">{range52}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
