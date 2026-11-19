import { Activity, Beaker, Bike, ChartNoAxesCombined, CircleHelp, GitBranch, Map, Menu, Moon, Network, Sun, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { About, Experiments, Forecasting, GraphExplorer, ModelComparison, Overview, StationAnalytics } from './pages'
import { useTheme } from './theme'

const links = [
  ['/', 'Overview', Activity], ['/graph', 'Graph Explorer', Map], ['/forecast', 'Demand Forecasting', ChartNoAxesCombined],
  ['/models', 'Model Comparison', GitBranch], ['/stations', 'Station Analytics', Bike], ['/experiments', 'Experiments Lab', Beaker], ['/about', 'About the Project', CircleHelp],
] as const

export default function App() {
  const [open, setOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()
  return <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
    <button className="mobile-menu fixed right-4 top-4 z-[1001] rounded-xl border border-white/10 bg-panel p-2 lg:hidden" onClick={() => setOpen(!open)} aria-label={open ? 'Close menu' : 'Open menu'}>{open ? <X/> : <Menu/>}</button>
    <aside className={`sidebar ${open ? 'translate-x-0' : '-translate-x-full'} fixed inset-y-0 z-[1000] flex w-[260px] flex-col border-r border-white/10 bg-[#0d1619]/95 p-5 backdrop-blur transition lg:sticky lg:top-0 lg:h-screen lg:translate-x-0`}>
      <div className="mb-10 flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-xl bg-emerald text-graphite shadow-[0_0_28px_rgba(16,185,129,.3)]"><Network/></div><div><p className="font-[Manrope] font-bold leading-tight">CitiBike GNN</p><p className="text-xs text-mint/60">LAB V2 · RESEARCH</p></div></div>
      <nav className="space-y-1">{links.map(([to,label,Icon]) => <NavLink key={to} to={to} end={to === '/'} onClick={()=>setOpen(false)} className={({isActive})=>`flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${isActive?'bg-emerald/15 text-mint':'text-slate-400 hover:bg-white/5 hover:text-white'}`}><Icon size={18}/>{label}</NavLink>)}</nav>
      <div className="mt-auto space-y-3 pt-6">
        <button type="button" onClick={toggleTheme} className="theme-toggle flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/[.035] px-3 py-3 text-sm text-slate-300 transition hover:border-emerald/40" aria-label={theme === 'dark' ? 'Activate light mode' : 'Activate dark mode'} aria-pressed={theme === 'light'}>
          <span className="flex items-center gap-3">{theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>} {theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
          <span className="theme-switch" aria-hidden="true"><span className="theme-switch-knob"/></span>
        </button>
        <div className="status-card rounded-xl border border-emerald/20 bg-emerald/5 p-3"><div className="mb-2 flex items-center gap-2 text-xs text-mint"><span className="h-2 w-2 rounded-full bg-emerald shadow-[0_0_9px_#10B981]"/> Artifact-backed</div><p className="text-[11px] leading-4 text-slate-500">Metrics are read from reproducible local outputs.</p></div>
      </div>
    </aside>
    <main className="min-w-0 p-5 pt-20 md:p-9 lg:p-12"><Routes><Route path="/" element={<Overview/>}/><Route path="/graph" element={<GraphExplorer/>}/><Route path="/forecast" element={<Forecasting/>}/><Route path="/models" element={<ModelComparison/>}/><Route path="/stations" element={<StationAnalytics/>}/><Route path="/experiments" element={<Experiments/>}/><Route path="/about" element={<About/>}/></Routes></main>
  </div>
}
