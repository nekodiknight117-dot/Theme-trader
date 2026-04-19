import { useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode, AreaSeries } from 'lightweight-charts'

export default function PriceChart({ ticker, priceHistory, loading = false, color = '#3b82f6' }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)

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
      timeScale: {
        borderColor: '#1e293b',
        textColor: '#94a3b8',
        timeVisible: true,
        secondsVisible: true,
      },
      width: containerRef.current.clientWidth,
      height: 260,
    })

    const series = chart.addSeries(AreaSeries, {
      lineColor: color,
      topColor: `${color}55`,
      bottomColor: `${color}00`,
      lineWidth: 2,
      priceLineVisible: true,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
    })

    chartRef.current = chart
    seriesRef.current = series

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [color])

  // Update series data when priceHistory changes
  useEffect(() => {
    if (!seriesRef.current || !priceHistory || priceHistory.length === 0) return
    seriesRef.current.setData(priceHistory)
    chartRef.current?.timeScale().fitContent()
  }, [priceHistory])

  const lastPrice = priceHistory.length > 0 ? priceHistory[priceHistory.length - 1].value : null

  return (
    <div className="price-chart-wrapper">
      <div className="price-chart-header">
        <span className="price-chart-ticker">{ticker}</span>
        {lastPrice != null && (
          <span className="price-chart-current">${lastPrice.toFixed(2)}</span>
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
