import { useState } from 'react'

const CATEGORY_COLORS = {
  'ETF':          '#3b82f6',
  'Blue Chip':    '#10b981',
  'Rising Star':  '#f59e0b',
  'IPO':          '#ec4899',
}

const TARGET_RETURN = { low: 8, medium: 18, high: 32 }

function pickColor(asset, index) {
  return CATEGORY_COLORS[asset.category] || `hsl(${(index * 67) % 360}, 70%, 55%)`
}

// Build SVG arc path for a donut segment
function arcPath(cx, cy, r, startAngle, endAngle) {
  const toRad = (deg) => (deg - 90) * (Math.PI / 180)
  const x1 = cx + r * Math.cos(toRad(startAngle))
  const y1 = cy + r * Math.sin(toRad(startAngle))
  const x2 = cx + r * Math.cos(toRad(endAngle))
  const y2 = cy + r * Math.sin(toRad(endAngle))
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`
}

function DonutChart({ assets, hoveredId, onHover }) {
  const SIZE = 220
  const cx = SIZE / 2
  const cy = SIZE / 2
  const R_OUTER = 90
  const R_INNER = 54
  const GAP = 2

  // Normalise weights in case they don't sum to exactly 1
  const totalWeight = assets.reduce((s, a) => s + (a.weight || 0), 0) || 1
  const normed = assets.map((a) => ({ ...a, w: (a.weight || 0) / totalWeight }))

  const segments = []
  let angle = 0
  normed.forEach((asset, i) => {
    const sweep = asset.w * 360
    const start = angle + GAP / 2
    const end = angle + sweep - GAP / 2
    if (sweep > GAP) {
      segments.push({ asset, i, start, end, color: pickColor(asset, i) })
    }
    angle += sweep
  })

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="donut-svg"
      aria-label="Fund allocation donut chart"
    >
      {segments.map(({ asset, i, start, end, color }) => {
        const isHovered = hoveredId === asset.id
        const outerR = isHovered ? R_OUTER + 5 : R_OUTER
        const outerPath = arcPath(cx, cy, outerR, start, end)
        const innerPath = arcPath(cx, cy, R_INNER, end, start)
        return (
          <path
            key={asset.id ?? i}
            d={`${outerPath} L ${innerPath.slice(2)} Z`}
            fill={color}
            opacity={hoveredId == null || isHovered ? 1 : 0.45}
            style={{ cursor: 'pointer', transition: 'opacity 0.15s, d 0.15s' }}
            onMouseEnter={() => onHover(asset.id)}
            onMouseLeave={() => onHover(null)}
          />
        )
      })}

      {/* Centre label */}
      <text x={cx} y={cy - 8} textAnchor="middle" className="donut-center-label">
        {assets.length}
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" className="donut-center-sub">
        holdings
      </text>
    </svg>
  )
}

function WeightTable({ assets, hoveredId, onHover }) {
  return (
    <table className="weight-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Category</th>
          <th>Weight</th>
          <th>Est. Return</th>
        </tr>
      </thead>
      <tbody>
        {assets.map((asset, i) => {
          const color = pickColor(asset, i)
          const weightPct = asset.weight != null ? (asset.weight * 100).toFixed(1) : '—'
          const cagrPct = asset.projected_cagr != null
            ? `${(asset.projected_cagr * 100).toFixed(1)}%`
            : '—'
          return (
            <tr
              key={asset.id ?? i}
              className={`weight-row ${hoveredId === asset.id ? 'weight-row--active' : ''}`}
              onMouseEnter={() => onHover(asset.id)}
              onMouseLeave={() => onHover(null)}
            >
              <td>
                <span className="weight-swatch" style={{ background: color }} />
                <strong>{asset.ticker}</strong>
              </td>
              <td>
                <span className="weight-cat-badge" style={{ color, background: `${color}22` }}>
                  {asset.category}
                </span>
              </td>
              <td className="weight-pct">{weightPct}%</td>
              <td className="weight-return">{cagrPct}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export default function FundViz({ assets, riskTolerance }) {
  const [hoveredId, setHoveredId] = useState(null)

  if (!assets || assets.length === 0) return null

  const risk = (riskTolerance || 'medium').toLowerCase()
  const targetReturn = TARGET_RETURN[risk] ?? 18
  const riskLabel = risk.charAt(0).toUpperCase() + risk.slice(1)

  // Compute the weighted average projected return of the actual portfolio
  const totalWeight = assets.reduce((s, a) => s + (a.weight || 0), 0) || 1
  const portfolioReturn = assets.reduce((s, a) => {
    return s + (a.projected_cagr || 0) * ((a.weight || 0) / totalWeight)
  }, 0)
  const portfolioReturnPct = (portfolioReturn * 100).toFixed(1)

  return (
    <div className="fund-viz">
      {/* Header row */}
      <div className="fund-viz-header">
        <div>
          <span className="section-tag">Fund Breakdown</span>
          <h2 className="fund-viz-title">Your Personalised Portfolio</h2>
        </div>
        <div className="fund-return-badges">
          <div className="fund-return-badge fund-return-badge--target">
            <span className="fund-return-label">Target Return</span>
            <span className="fund-return-value">~{targetReturn}% / yr</span>
            <span className="fund-return-sub">{riskLabel} risk profile</span>
          </div>
          <div className="fund-return-badge fund-return-badge--projected">
            <span className="fund-return-label">Projected Return</span>
            <span className="fund-return-value">{portfolioReturnPct}% / yr</span>
            <span className="fund-return-sub">weighted avg. of holdings</span>
          </div>
        </div>
      </div>

      {/* Chart + Table */}
      <div className="fund-viz-body">
        <div className="donut-wrapper">
          <DonutChart assets={assets} hoveredId={hoveredId} onHover={setHoveredId} />
        </div>
        <div className="weight-table-wrapper">
          <WeightTable assets={assets} hoveredId={hoveredId} onHover={setHoveredId} />
        </div>
      </div>
    </div>
  )
}
