import { Component } from 'react'
import { Link } from 'react-router-dom'

/**
 * Catches render errors in route trees so a failed chart/table does not leave a blank screen.
 */
export default class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { err: null }
  }

  static getDerivedStateFromError(err) {
    return { err }
  }

  componentDidCatch(err, info) {
    console.error('[RouteErrorBoundary]', err, info?.componentStack)
  }

  render() {
    if (this.state.err) {
      return (
        <div className="dashboard-page">
          <div className="dashboard-error" style={{ padding: '48px 24px' }}>
            <h2>Something broke on this page</h2>
            <p style={{ color: 'var(--text-muted, #9ca3af)', marginBottom: 16 }}>
              {this.state.err?.message || 'Unexpected error'}
            </p>
            <Link to="/" className="btn-primary">
              Go home
            </Link>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
