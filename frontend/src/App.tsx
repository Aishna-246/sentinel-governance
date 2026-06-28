import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'

type NavItem = {
  to: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { to: '/', label: 'Overview', icon: '🏠' },
  { to: '/models', label: 'Models', icon: '📦' },
  { to: '/lineage', label: 'Lineage', icon: '🔗' },
  { to: '/scanner', label: 'PII Scanner', icon: '🔍' },
  { to: '/egress', label: 'Vendor Flows', icon: '🌐' },
  { to: '/decisions', label: 'Decisions', icon: '📋' },
  { to: '/report', label: 'Report', icon: '📄' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
]

function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-50 p-8 shadow-sm">
      <h2 className="text-2xl font-semibold text-slate-800">{title}</h2>
      <p className="mt-2 text-sm text-slate-500">{title} page coming soon.</p>
    </section>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
        <div
          style={{
            width: '240px',
            minWidth: '240px',
            backgroundColor: '#1A3C5E',
            height: '100vh',
            overflowY: 'auto',
            fontFamily: 'system-ui, sans-serif',
          }}
        >
          <aside className="flex h-full flex-col justify-between px-5 py-6 text-white shadow-xl">
            <div>
              <div className="mb-8">
                <h1 className="text-2xl font-black tracking-[0.2em]">SENTINEL</h1>
                <p className="mt-1 text-sm text-slate-300">AI Governance Platform</p>
              </div>

              <nav className="space-y-1">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    style={({ isActive }) =>
                      isActive
                        ? {
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '10px 16px',
                            borderRadius: '8px',
                            textDecoration: 'none',
                            fontSize: '14px',
                            fontWeight: 500,
                            color: 'white',
                            marginBottom: '4px',
                            transition: 'background 0.15s',
                            backgroundColor: 'rgba(255,255,255,0.15)',
                          }
                        : {
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '10px 16px',
                            borderRadius: '8px',
                            textDecoration: 'none',
                            fontSize: '14px',
                            fontWeight: 500,
                            color: 'white',
                            marginBottom: '4px',
                            transition: 'background 0.15s',
                          }
                    }
                  >
                    <span style={{ fontSize: '16px' }}>{item.icon}</span>
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </nav>
            </div>

            <div className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span>DPDP Active</span>
              </div>
            </div>
          </aside>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', backgroundColor: 'white', padding: '32px' }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/models" element={<PlaceholderPage title="Models" />} />
            <Route path="/lineage" element={<PlaceholderPage title="Lineage" />} />
            <Route path="/scanner" element={<PlaceholderPage title="PII Scanner" />} />
            <Route path="/egress" element={<PlaceholderPage title="Vendor Flows" />} />
            <Route path="/decisions" element={<PlaceholderPage title="Decisions" />} />
            <Route path="/report" element={<PlaceholderPage title="Report" />} />
            <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
