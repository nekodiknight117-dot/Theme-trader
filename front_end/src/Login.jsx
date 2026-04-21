import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import './OnboardingForm.css'
import { API_URL } from './config.js'

const API = API_URL

export default function Login() {
  const navigate = useNavigate()
  const { loginWithToken } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const d = data.detail
        const msg =
          typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg || x).join(', ') : 'Login failed'
        throw new Error(msg)
      }
      loginWithToken(data.access_token, data.user)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="onboarding-page">
      <nav className="onboarding-nav">
        <Link to="/" className="navbar-logo" style={{ textDecoration: 'none' }}>
          Theme<span>Trader</span>
        </Link>
      </nav>

      <div className="onboarding-container" style={{ maxWidth: 440 }}>
        <div className="onboarding-header">
          <span className="section-tag">Welcome back</span>
          <h1>Log in</h1>
          <p>View your personalised fund and holdings.</p>
        </div>

        <form className="onboarding-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="login-user">Username</label>
            <input
              id="login-user"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="login-pass">Password</label>
            <input
              id="login-pass"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn-primary form-submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 24, color: 'var(--text-muted, #64748b)' }}>
          New here?{' '}
          <Link to="/onboarding" style={{ color: 'var(--accent, #6366f1)', fontWeight: 600 }}>
            Build your fund
          </Link>
        </p>
      </div>
    </div>
  )
}
