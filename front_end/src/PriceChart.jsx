import { useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode, AreaSeries, LineSeries } from 'lightweight-charts'

/** @typedef {{ time: number, value: number }[]} PointSeries */

function normalizePctFromFirst(points) {
  if (!points?.length) return []
  const p0 = points[0].value
  if (p0 == null || p0 === 0) return []
  return points.map((p) => ({ time: p.time, value: 100 * (p.value / p0 - 1) }))
}

export default function PriceChart({
  ticker,
  priceHistory,
  loading = false,
  color = '#3b82f6',
  /** Raw OHLC-style points for indexes; chart normalizes to % change from first bar. */
  overlayPrices = { dji: null, spx: null, ixic: null },
  overlayEnabled = { dji: false, spx: false, ixic: false },
}) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const primaryRef = useRef(null)
  const overlayRefs = useRef({})

  const hasOverlay =
    (overlayEnabled.dji && overlayPrices.dji?.length) ||
    (overlayEnabled.spx && overlayPrices.spx?.length) ||
    (overlayEnabled.ixic && overlayPrices.ixic?.length)

  const compareMode = Boolean(hasOverlay)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#1e293b',
        textColor: '#94a3b8',
      },
      localization: compareMode
        ? {
            priceFormatter: (p) => `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`,
          }
        : {},
      timeScale: {
        borderColor: '#1e293b',
        textColor: '#94a3b8',
        timeVisible: true,
        secondsVisible: true,
      },
      width: Math.max(containerRef.current.clientWidth || 0, 2),
      height: 280,
    })

    let primary
    if (compareMode) {
      primary = chart.addSeries(LineSeries, {
        color,
        lineWidth: 2,
        priceLineVisible: true,
        lastValueVisible: true,
        crosshairMarkerVisible: true,
      })
    } else {
      primary = chart.addSeries(AreaSeries, {
        lineColor: color,
        topColor: `${color}55`,
        bottomColor: `${color}00`,
        lineWidth: 2,
        priceLineVisible: true,
        lastValueVisible: true,
        crosshairMarkerVisible: true,
      })
    }

    chartRef.current = chart
    primaryRef.current = primary
    overlayRefs.current = {}

    if (compareMode) {
      const specs = [
        { key: 'dji', lineColor: '#e2e8f0' },
        { key: 'spx', lineColor: '#38bdf8' },
        { key: 'ixic', lineColor: '#f472b6' },
      ]
      for (const s of specs) {
        if (!overlayEnabled[s.key]) continue
        const ser = chart.addSeries(LineSeries, {
          color: s.lineColor,
          lineWidth: 1.5,
          priceLineVisible: false,
          lastValueVisible: true,
        })
        overlayRefs.current[s.key] = ser
      }
    }

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: Math.max(containerRef.current.clientWidth || 0, 2) })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
      primaryRef.current = null
      overlayRefs.current = {}
    }
  }, [color, compareMode, overlayEnabled.dji, overlayEnabled.spx, overlayEnabled.ixic])

  // Must re-run whenever the chart is recreated (same deps as chart `useEffect` below).
  // Otherwise toggling a second benchmark rebuilds the chart but leaves the primary series empty
  // while overlay series get data from the overlay effect — user only sees indexes.
  useEffect(() => {
    const primary = primaryRef.current
    if (!primary || !priceHistory || priceHistory.length === 0) return
    if (compareMode) {
      primary.setData(normalizePctFromFirst(priceHistory))
    } else {
      primary.setData(priceHistory)
    }
    chartRef.current?.timeScale().fitContent()
  }, [
    priceHistory,
    compareMode,
    color,
    overlayEnabled.dji,
    overlayEnabled.spx,
    overlayEnabled.ixic,
  ])

  useEffect(() => {
    if (!compareMode) return
    const specs = [
      { key: 'dji', raw: overlayPrices.dji },
      { key: 'spx', raw: overlayPrices.spx },
      { key: 'ixic', raw: overlayPrices.ixic },
    ]
    for (const s of specs) {
      const ser = overlayRefs.current[s.key]
      if (!ser || !s.raw?.length) continue
      ser.setData(normalizePctFromFirst(s.raw))
    }
    chartRef.current?.timeScale().fitContent()
  }, [compareMode, overlayPrices, overlayEnabled.dji, overlayEnabled.spx, overlayEnabled.ixic])

  const lastRaw = priceHistory.length > 0 ? priceHistory[priceHistory.length - 1].value : null
  const lastPct =
    compareMode && priceHistory.length > 0
      ? normalizePctFromFirst(priceHistory).slice(-1)[0]?.value
      : null

  return (
    <div className="price-chart-wrapper">
      <div className="price-chart-header">
        <span className="price-chart-ticker">{ticker}</span>
        {compareMode && (
          <span className="price-chart-mode-tag">vs indexes · % change from first bar</span>
        )}
        {!compareMode && lastRaw != null && Number.isFinite(Number(lastRaw)) && (
          <span className="price-chart-current">${Number(lastRaw).toFixed(2)}</span>
        )}
        {compareMode && lastPct != null && Number.isFinite(Number(lastPct)) && (
          <span className="price-chart-current">{Number(lastPct) >= 0 ? '+' : ''}{Number(lastPct).toFixed(2)}%</span>
        )}
        {loading && <span className="price-chart-loading">Loading…</span>}
      </div>
      <div ref={containerRef} className="price-chart-container" />
      {!loading && priceHistory.length === 0 && (
        <div className="price-chart-empty">No price data available</div>
      )}
    </div>
  )
}
