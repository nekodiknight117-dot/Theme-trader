const CATEGORY_META = {
  'ETF':         { emoji: '📊', color: '#3b82f6' },
  'Blue Chip':   { emoji: '💎', color: '#10b981' },
  'Rising Star': { emoji: '🚀', color: '#f59e0b' },
  'IPO':         { emoji: '✨', color: '#ec4899' },
}

function pct(value) {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function ReturnBadge({ value }) {
  if (value == null) return <span className="return-badge return-badge--neutral">—</span>
  const cls = value >= 0 ? 'return-badge--pos' : 'return-badge--neg'
  return <span className={`return-badge ${cls}`}>{pct(value)}</span>
}

export default function FundSummary({ assets, prevClose, expectedReturn = {}, livePrices, seedBarsRef }) {
  const n = assets.length
  if (n === 0) return null

  // --- per-asset current price: live > last seed bar > null ---
  function currentPrice(ticker) {
    if (livePrices[ticker] != null) return livePrices[ticker]
    const bars = seedBarsRef?.current?.[ticker]
    if (bars && bars.length > 0) return bars[bars.length - 1].value
    return null
  }

  // --- per-asset daily return ---
  function assetReturn(ticker) {
    const cur = currentPrice(ticker)
    const pc = prevClose[ticker]
    if (cur == null || pc == null || pc === 0) return null
    return ((cur - pc) / pc) * 100
  }

  // --- equal-weighted fund daily return ---
  const returns = assets.map((a) => assetReturn(a.ticker)).filter((r) => r != null)
  const fundReturn = returns.length > 0
    ? returns.reduce((s, r) => s + r, 0) / returns.length
    : null

  // --- equal-weighted fund expected return (1Y CAGR) ---
  const expReturns = assets.map((a) => expectedReturn[a.ticker]).filter((r) => r != null)
  const fundExpectedReturn = expReturns.length > 0
    ? expReturns.reduce((s, r) => s + r, 0) / expReturns.length
    : null

  // --- category allocation (equal weight per asset) ---
  const catCounts = {}
  for (const a of assets) {
    catCounts[a.category] = (catCounts[a.category] || 0) + 1
  }
  const catOrder = Object.keys(catCounts).sort(
    (a, b) => catCounts[b] - catCounts[a]
  )

  return (
    <div className="fund-summary">
      {/* ── top row ── */}
      <div className="fund-summary-top">
        <div className="fund-kpi">
          <span className="fund-kpi-label">Today's Return</span>
          <ReturnBadge value={fundReturn} />
        </div>
        <div className="fund-kpi fund-kpi--highlight">
          <span className="fund-kpi-label">Expected Return (1Y)</span>
          {fundExpectedReturn != null
            ? <ReturnBadge value={fundExpectedReturn} />
            : <span className="fund-kpi-loading">Calculating…</span>}
        </div>
        <div className="fund-kpi">
          <span className="fund-kpi-label">Assets</span>
          <span className="fund-kpi-value">{n}</span>
        </div>
        <div className="fund-kpi">
          <span className="fund-kpi-label">Weighting</span>
          <span className="fund-kpi-value">Equal ({(100 / n).toFixed(1)}% each)</span>
        </div>
      </div>

      {/* ── allocation bar ── */}
      <div className="alloc-section">
        <span className="alloc-label">Allocation by Category</span>
        <div className="alloc-bar">
          {catOrder.map((cat) => {
            const weight = (catCounts[cat] / n) * 100
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
            const weight = (catCounts[cat] / n) * 100
            const meta = CATEGORY_META[cat] || { emoji: '📈', color: '#7c3aed' }
            return (
              <div key={cat} className="alloc-legend-item">
                <span className="alloc-dot" style={{ background: meta.color }} />
                <span className="alloc-legend-name">{meta.emoji} {cat}</span>
                <span className="alloc-legend-pct">{weight.toFixed(1)}%</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── per-asset return table ── */}
      <div className="asset-returns">
        <span className="alloc-label">Individual Returns</span>
        <div className="asset-returns-table">
          <div className="asset-returns-header">
            <span>Ticker</span>
            <span>Price</span>
            <span>Prev Close</span>
            <span>Today</span>
            <span>Expected (1Y)</span>
          </div>
          {assets.map((a) => {
            const ret = assetReturn(a.ticker)
            const exp = expectedReturn[a.ticker] ?? null
            const cur = currentPrice(a.ticker)
            const pc = prevClose[a.ticker]
            const meta = CATEGORY_META[a.category] || { color: '#7c3aed' }
            return (
              <div key={a.ticker} className="asset-return-row">
                <span className="asset-return-ticker" style={{ color: meta.color }}>
                  {a.ticker}
                </span>
                <span className="asset-return-price">
                  {cur != null ? `$${cur.toFixed(2)}` : '—'}
                </span>
                <span className="asset-return-prev">
                  {pc != null ? `$${pc.toFixed(2)}` : '—'}
                </span>
                <ReturnBadge value={ret} />
                <ReturnBadge value={exp} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
