import { useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import './App.css'
import OnboardingForm from './OnboardingForm.jsx'
import Dashboard from './Dashboard.jsx'
import Login from './Login.jsx'
import ProtectedRoute from './ProtectedRoute.jsx'

const THEMES = [
  {
    icon: '🌱',
    name: 'Clean Energy',
    desc: 'Solar, wind, and battery tech companies driving the energy transition.',
    tag: 'ESG',
  },
  {
    icon: '🤖',
    name: 'AI & Tech',
    desc: 'The companies building the next generation of artificial intelligence.',
    tag: 'Growth',
  },
  {
    icon: '🏥',
    name: 'Healthcare',
    desc: 'Biotech, medical devices, and digital health innovators.',
    tag: 'Defensive',
  },
  {
    icon: '🚀',
    name: 'Space',
    desc: 'Satellites, launch vehicles, and space-infrastructure pioneers.',
    tag: 'Emerging',
  },
  {
    icon: '🎮',
    name: 'Gaming',
    desc: 'Video games, esports, and interactive entertainment leaders.',
    tag: 'Consumer',
  },
  {
    icon: '🏙️',
    name: 'Real Estate',
    desc: 'REITs and proptech transforming how people live and work.',
    tag: 'Income',
  },
]

const STEPS = [
  {
    n: '1',
    title: 'Pick Your Interests',
    desc: 'Tell us what sectors and topics matter to you.',
  },
  {
    n: '2',
    title: 'Share Your Goals',
    desc: 'Set your risk tolerance, timeline, and return targets.',
  },
  {
    n: '3',
    title: 'We Build the Fund',
    desc: 'Our engine assembles a diversified portfolio around your themes.',
  },
  {
    n: '4',
    title: 'You Invest',
    desc: 'Review, approve, and start growing with a fund made for you.',
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
          <li><a href="#themes">Themes</a></li>
          <li><a href="#pricing">Pricing</a></li>
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
          ✦ Personalized investing, finally
        </div>
        <h1>
          Invest in what<br />
          <em>you believe in</em>
        </h1>
        <p className="hero-sub">
          ThemeTrader builds you a custom fund around your interests —
          clean energy, AI, healthcare, or anything that excites you.
          No jargon. No cookie-cutter portfolios.
        </p>
        <div className="hero-actions">
          <Link to="/onboarding" className="btn-primary">
            Build My Fund →
          </Link>
          <a href="#themes" className="btn-ghost">
            See Themes
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
        <h2 className="section-heading">From interests to investments in minutes</h2>
        <p className="section-sub">
          Four simple steps turn your passions into a portfolio that's
          uniquely yours.
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

function ThemeCards() {
  return (
    <section className="section" id="themes">
      <div className="section-inner">
        <span className="section-tag">Themes</span>
        <h2 className="section-heading">Explore investment themes</h2>
        <p className="section-sub">
          Choose one or mix and match — we handle the diversification.
        </p>
        <div className="themes-grid">
          {THEMES.map((t) => (
            <div className="theme-card" key={t.name}>
              <span className="theme-icon">{t.icon}</span>
              <h3>{t.name}</h3>
              <p>{t.desc}</p>
              <span className="theme-pill">{t.tag}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Stats() {
  return (
    <section className="stats">
      <div className="stats-inner">
        <div className="stat-item">
          <div className="stat-number">50+</div>
          <div className="stat-label">Investment themes</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">12k+</div>
          <div className="stat-label">Investors on platform</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">$0</div>
          <div className="stat-label">Commission fees</div>
        </div>
      </div>
    </section>
  )
}

function CtaBanner() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (email.trim()) setSubmitted(true)
  }

  return (
    <section className="cta-banner" id="get-started">
      <div className="section-inner">
        <span className="section-tag">Get Started</span>
        <h2 className="section-heading">Ready to build your fund?</h2>
        <p className="section-sub">
          Join thousands of investors who grow their wealth around what they
          care about. It's free to start.
        </p>
        {submitted ? (
          <p style={{ marginTop: 36, fontWeight: 600, color: 'var(--accent)', fontSize: 17 }}>
            ✓ We'll be in touch soon!
          </p>
        ) : (
          <form className="cta-form" onSubmit={handleSubmit}>
            <input
              className="cta-input"
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <button type="submit" className="btn-primary">
              Join Free
            </button>
          </form>
        )}
        <Link to="/onboarding" className="btn-primary" style={{ marginTop: 16, display: 'inline-block' }}>
          Build My Fund Now →
        </Link>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="footer" id="pricing">
      <div className="footer-inner">
        <div className="footer-top">
          <div className="footer-brand">
            <span className="navbar-logo" style={{ fontSize: 18 }}>
              Theme<span>Trader</span>
            </span>
            <p>
              Personalized funds built around your interests.
              Smarter investing starts here.
            </p>
          </div>
          <div className="footer-col">
            <h4>Product</h4>
            <ul>
              <li><a href="#how-it-works">How It Works</a></li>
              <li><a href="#themes">Themes</a></li>
              <li><a href="#pricing">Pricing</a></li>
              <li><a href="#get-started">Get Started</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Company</h4>
            <ul>
              <li><a href="#">About Us</a></li>
              <li><a href="#">Blog</a></li>
              <li><a href="#">Careers</a></li>
              <li><a href="#">Press</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Legal</h4>
            <ul>
              <li><a href="#">Terms of Service</a></li>
              <li><a href="#">Privacy Policy</a></li>
              <li><a href="#">Disclosures</a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© 2026 ThemeTrader. All rights reserved. Not financial advice.</p>
          <div className="footer-bottom-links">
            <a href="#">Twitter / X</a>
            <a href="#">LinkedIn</a>
            <a href="#">Discord</a>
          </div>
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
      <ThemeCards />
      <Stats />
      <CtaBanner />
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
            <Dashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
