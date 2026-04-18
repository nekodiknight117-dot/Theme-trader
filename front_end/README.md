# Theme-Trader Frontend

The frontend is a **React + Vite** single-page application that connects to the Theme-Trader FastAPI backend to display personalized, AI-generated investment portfolios in real time.

---

## Prerequisites

- [Node.js](https://nodejs.org/) **v18 or higher**
- `npm` (bundled with Node.js)
- The **backend server** must be running at `http://127.0.0.1:8000` before the frontend will function correctly. See [`backend/README.md`](../backend/README.md) for setup instructions.

---

## Quick Start (Development)

```bash
# 1. Navigate to the frontend directory
cd front_end

# 2. Install dependencies
npm install

# 3. Start the development server with Hot Module Replacement (HMR)
npm run dev
```

The app will be available at **`http://localhost:5173`** by default.

> **Note:** Vite's dev server proxies API requests to the backend. Make sure `uv run uvicorn app.main:app --reload` is running in the `backend/` directory in a separate terminal.

---

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite dev server with HMR at `localhost:5173` |
| `npm run build` | Compile and bundle the app for production into `dist/` |
| `npm run preview` | Serve the production `dist/` build locally for testing |
| `npm run lint` | Run ESLint across all source files |

---

## Project Structure

```
front_end/
├── public/               # Static assets served as-is
├── src/
│   ├── main.jsx          # App entry point — mounts React to the DOM
│   ├── App.jsx           # Root component, routing, and auth state
│   ├── App.css           # Global application styles
│   ├── Dashboard.jsx     # Main dashboard — portfolio display & real-time prices
│   ├── Dashboard.css     # Dashboard component styles
│   ├── OnboardingForm.jsx # User onboarding flow (interests, risk tolerance)
│   ├── OnboardingForm.css # Onboarding form styles
│   └── index.css         # Base/reset styles
├── index.html            # HTML shell — Vite injects the bundled JS here
├── vite.config.js        # Vite configuration
├── package.json          # Dependencies and npm scripts
└── eslint.config.js      # ESLint rules
```

---

## Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `react` | ^19 | UI library |
| `react-dom` | ^19 | DOM renderer |
| `react-router-dom` | ^7 | Client-side routing |
| `vite` | ^8 | Build tool and dev server |
| `@vitejs/plugin-react` | ^6 | React Fast Refresh + JSX transform |

---

## Backend Integration

The frontend communicates with the backend via two channels:

1. **REST API** — `http://127.0.0.1:8000/api/...`
   - `POST /api/users` — Register a new user
   - `POST /api/assess` — Trigger AI portfolio generation for a user
   - `GET /api/portfolios/{user_id}` — Fetch a user's saved portfolio

2. **WebSocket** — `ws://127.0.0.1:8000/ws/prices`
   - Streams real-time stock price updates from Alpaca directly into the Dashboard

---

## Production Build

To generate a production-optimized bundle:

```bash
cd front_end
npm run build
```

Output is written to `front_end/dist/`. You can serve this directory with any static file host or preview it locally:

```bash
npm run preview
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `npm run dev` fails | Run `npm install` first to restore `node_modules` |
| Blank page / API errors | Confirm the backend is running at `http://127.0.0.1:8000` |
| WebSocket not connecting | Check that `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are set in `backend/.env` |
| Port 5173 already in use | Vite will auto-increment to the next free port — check the terminal output |
