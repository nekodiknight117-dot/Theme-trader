import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import './OnboardingForm.css'

const API = 'http://localhost:8000'

const STEP_TELL_US = 'tell-us'
const STEP_REVIEW = 'review'
const STEP_GENERATING = 'generating'

export default function OnboardingForm() {
  const navigate = useNavigate()
  const { loginWithToken } = useAuth()

  const [step, setStep] = useState(STEP_TELL_US)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [rawText, setRawText] = useState('')
  const [riskTolerance, setRiskTolerance] = useState('medium')

  const [parsed, setParsed] = useState(null)
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState('')

  async function handleAnalyse(e) {
    e.preventDefault()
    if (!username.trim() || !rawText.trim() || !password) {
      setError('Please fill in all fields before continuing.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setError('')
    setParsing(true)
    try {
      const res = await fetch(`${API}/api/parse-interests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: rawText }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setParsed(data)
      setStep(STEP_REVIEW)
    } catch (err) {
      setError(`Failed to analyse your interests: ${err.message}`)
    } finally {
      setParsing(false)
    }
  }

  async function handleConfirm() {
    setStep(STEP_GENERATING)
    setError('')
    try {
      const regRes = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password,
          risk_tolerance: riskTolerance,
          interests: parsed.interests,
        }),
      })
      const regData = await regRes.json().catch(() => ({}))
      if (!regRes.ok) {
        throw new Error(regData.detail || `Registration failed: ${regRes.status}`)
      }
      loginWithToken(regData.access_token, regData.user)

      const assessRes = await fetch(`${API}/api/assess`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${regData.access_token}` },
      })
      if (!assessRes.ok) {
        const detail = await assessRes.json().catch(() => ({}))
        throw new Error(detail.detail || `Assessment failed: ${assessRes.status}`)
      }
      const assessData = await assessRes.json()
      console.log('[OnboardingForm] user:', user)
      console.log('[OnboardingForm] assess response:', assessData)

      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
      setStep(STEP_REVIEW)
    }
  }

  return (
    <div className="onboarding-page">
      <nav className="onboarding-nav">
        <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
          Theme<span>Trader</span>
        </Link>
      </nav>

      <div className="onboarding-container">
        {step === STEP_TELL_US && (
          <>
            <div className="onboarding-header">
              <span className="section-tag">Step 1 of 2</span>
              <h1>Tell us about yourself</h1>
              <p>Describe your interests and investment goals in your own words — our AI does the rest.</p>
            </div>

            <form className="onboarding-form" onSubmit={handleAnalyse}>
              <div className="form-group">
                <label htmlFor="username">Choose a username</label>
                <input
                  id="username"
                  type="text"
                  className="form-input"
                  placeholder="e.g. alex_invests"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  className="form-input"
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  minLength={6}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="rawText">Your interests &amp; goals</label>
                <textarea
                  id="rawText"
                  className="form-textarea"
                  rows={6}
                  placeholder={
                    "e.g. I love following AI and robotics startups, and I care about clean energy. " +
                    "I want to grow my wealth over the long term and am comfortable with some risk."
                  }
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  required
                />
                <span className="form-hint">Write naturally — the AI will extract your themes.</span>
              </div>

              <div className="form-group">
                <label>Risk tolerance</label>
                <div className="risk-options">
                  {['low', 'medium', 'high'].map((r) => (
                    <label key={r} className={`risk-pill ${riskTolerance === r ? 'selected' : ''}`}>
                      <input
                        type="radio"
                        name="risk"
                        value={r}
                        checked={riskTolerance === r}
                        onChange={() => setRiskTolerance(r)}
                      />
                      {r.charAt(0).toUpperCase() + r.slice(1)}
                    </label>
                  ))}
                </div>
              </div>

              {error && <p className="form-error">{error}</p>}

              <button type="submit" className="btn-primary form-submit" disabled={parsing}>
                {parsing ? 'Analysing…' : 'Analyse My Interests →'}
              </button>
            </form>
          </>
        )}

        {step === STEP_REVIEW && parsed && (
          <>
            <div className="onboarding-header">
              <span className="section-tag">Step 2 of 2</span>
              <h1>Review &amp; Confirm</h1>
              <p>Here's what our AI understood from your description. Confirm to generate your fund.</p>
            </div>

            <div className="review-card">
              <div className="review-row">
                <span className="review-label">Username</span>
                <span className="review-value">{username}</span>
              </div>
              <div className="review-row">
                <span className="review-label">Investment themes</span>
                <span className="review-value">{parsed.interests}</span>
              </div>
              <div className="review-row">
                <span className="review-label">Inferred goal</span>
                <span className="review-value goal-badge">{parsed.investment_goals}</span>
              </div>
              <div className="review-row">
                <span className="review-label">Risk tolerance</span>
                <span className="review-value risk-badge">{riskTolerance}</span>
              </div>
            </div>

            {error && <p className="form-error">{error}</p>}

            <div className="review-actions">
              <button className="btn-ghost" onClick={() => setStep(STEP_TELL_US)}>
                ← Edit
              </button>
              <button className="btn-primary" onClick={handleConfirm}>
                Build My Fund →
              </button>
            </div>
          </>
        )}

        {step === STEP_GENERATING && (
          <div className="generating-state">
            <div className="spinner" aria-label="Loading" />
            <h2>Building your personalised fund…</h2>
            <p>We're selecting stocks, pulling research, and writing your investment rationale. This may take up to a minute.</p>
          </div>
        )}
      </div>
    </div>
  )
}
