import { useState, useEffect } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import './App.css'
import OnboardingForm from './OnboardingForm.jsx'
import Dashboard from './Dashboard.jsx'
import Login from './Login.jsx'
import ProtectedRoute from './ProtectedRoute.jsx'
import RouteErrorBoundary from './RouteErrorBoundary.jsx'
import { CATEGORY_META } from './categoryMeta.js'

const API = 'http://localhost:8000'

/** Shown when the DB has no assets yet or the API fails—matches dashboard category buckets. */
const FALLBACK_LANDING_EXAMPLES = [
  {
    ticker: 'SPY',
    name: 'SPDR S&P 500 ETF Trust',
    category: 'ETF',
    rationale_preview:
      'ETF slots lean toward broad market exposure—your risk level controls how many you get.',
  },
  {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    category: 'Blue Chip',
    rationale_preview:
      'Blue chips emphasize established names; after signup you will see AI rationales tied to your profile.',
  },
  {
    ticker: 'NVDA',
    name: 'NVIDIA Corporation',
    category: 'Rising Star',
    rationale_preview:
      'Growth-oriented names rank on recent performance—higher risk profiles include more of this bucket.',
  },
  {
    ticker: 'COIN',
    name: 'Coinbase Global Inc.',
    category: 'IPO',
    rationale_preview:
      'Newer listings can surface in the IPO category when risk tolerance allows.',
  },
]

const STEPS = [
  {
    n: '1',
    title: 'Describe your interests',
    desc: 'Write a short paragraph about what you care about and your goals—we parse themes from your own words.',
  },
  {
    n: '2',
    title: 'Choose risk tolerance',
    desc: 'Pick low, medium, or high. It sets the mix across ETFs, blue chips, IPOs, and growth-oriented names.',
  },
  {
    n: '3',
    title: 'We build a ranked portfolio',
    desc: 'We score candidates on recent market data and, when possible, use theme-aware ticker lists—then add research-informed AI rationales.',
  },
  {
    n: '4',
    title: 'Review on your dashboard',
    desc: 'See holdings, charts, live prices, and rationale copy. ThemeTrader does not place trades for you in the app.',
  },
]

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
          Theme<span>Trader</span>
        </Link>
        <ul className="navbar-links">
          <li><a href="#how-it-works">How It Works</a></li>
          <li><a href="#examples">Examples</a></li>
        </ul>
        <Link to="/login" className="btn-ghost" style={{ marginRight: 12, fontSize: 15 }}>
          Log in
        </Link>
        <Link to="/onboarding" className="navbar-cta">Get Started</Link>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="hero">
      <div className="hero-blob" aria-hidden="true" />
      <div className="hero-inner">
        <div className="hero-badge">
          ✦ Theme-aligned portfolio ideas
        </div>
        <h1>
          Invest in what<br />
          <em>you believe in</em>
        </h1>
        <p className="hero-sub">
          Describe your interests in your own words, set a risk level, and get a
          sample portfolio of stocks and ETFs—ranked on recent market data, with
          short AI-written rationales grounded in public research. Explore results
          on your dashboard; this isn&apos;t brokerage or trade execution.
        </p>
        <div className="hero-actions">
          <Link to="/onboarding" className="btn-primary">
            Build my portfolio →
          </Link>
          <a href="#examples" className="btn-ghost">
            See examples
          </a>
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section className="section how-it-works" id="how-it-works">
      <div className="section-inner">
        <span className="section-tag">How It Works</span>
        <h2 className="section-heading">From interests to a ranked portfolio</h2>
        <p className="section-sub">
          Signup is one paragraph plus risk—then we run the selection and rationale
          pipeline below.
        </p>
        <div className="steps-grid">
          {STEPS.map((step) => (
            <div className="step-card" key={step.n}>
              <div className="step-number">{step.n}</div>
              <h3>{step.title}</h3>
              <p>{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function LandingExamplesSection() {
  const [examples, setExamples] = useState(null)
  const [fromDatabase, setFromDatabase] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await fetch(`${API}/api/landing-examples`)
        if (!res.ok) throw new Error(String(res.status))
        const data = await res.json()
        if (cancelled) return
        if (Array.isArray(data) && data.length > 0) {
          setExamples(data)
          setFromDatabase(true)
        } else {
          setExamples(FALLBACK_LANDING_EXAMPLES)
          setFromDatabase(false)
        }
      } catch {
        if (!cancelled) {
          setExamples(FALLBACK_LANDING_EXAMPLES)
          setFromDatabase(false)
        }
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const header = (
    <>
      <span className="section-tag">Dashboard preview</span>
      <h2 className="section-heading">Holdings use these four categories</h2>
      <p className="section-sub">
        Each row matches what you&apos;ll see after signup: ticker, company name, category badge,
        and rationale text. Samples come from the latest portfolio stored in the database when
        available; otherwise we show the same structure with representative tickers.
        {examples !== null &&
          (fromDatabase ? (
            <span className="examples-source-note"> Live examples from the most recent assessment.</span>
          ) : (
            <span className="examples-source-note"> Placeholders until your first portfolio is generated.</span>
          ))}
      </p>
    </>
  )

  if (examples === null) {
    return (
      <section className="section" id="examples">
        <div className="section-inner">
          {header}
          <p className="examples-loading" role="status">
            Loading sample holdings…
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="section" id="examples">
      <div className="section-inner">
        {header}
        <div className="examples-grid">
          {examples.map((asset) => {
            const meta = CATEGORY_META[asset.category] || { emoji: '📈', color: '#7c3aed' }
            return (
              <article className="example-holding-card" key={`${asset.ticker}-${asset.category}`}>
                <div className="example-holding-header">
                  <div className="example-holding-titles">
                    <span className="example-holding-ticker">{asset.ticker}</span>
                    {asset.name && asset.name !== asset.ticker && (
                      <span className="example-holding-name">{asset.name}</span>
                    )}
                  </div>
                  <span
                    className="example-holding-badge"
                    style={{
                      background: `${meta.color}22`,
                      color: meta.color,
                    }}
                  >
                    {meta.emoji} {asset.category}
                  </span>
                </div>
                {asset.rationale_preview && (
                  <p className="example-holding-rationale">{asset.rationale_preview}</p>
                )}
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-top">
          <div className="footer-brand">
            <span className="navbar-logo" style={{ fontSize: 18 }}>
              Theme<span>Trader</span>
            </span>
            <p>
              Theme-aligned portfolio ideas from your interests—not a fund product.
              For exploration and learning; not a substitute for your own research.
            </p>
          </div>
          <div className="footer-col">
            <h4>Product</h4>
            <ul>
              <li><a href="#how-it-works">How It Works</a></li>
              <li><a href="#examples">Examples</a></li>
              <li><Link to="/onboarding">Get Started</Link></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© 2026 ThemeTrader. All rights reserved. Not financial advice.</p>
        </div>
      </div>
    </footer>
  )
}

function LandingPage() {
  return (
    <div className="page">
      <Navbar />
      <Hero />
      <HowItWorks />
      <LandingExamplesSection />
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={<OnboardingForm />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <RouteErrorBoundary>
              <Dashboard />
            </RouteErrorBoundary>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
