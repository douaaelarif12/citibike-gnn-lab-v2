import { ReactNode } from 'react'
import { LoaderCircle, TriangleAlert } from 'lucide-react'

export function PageHeader({ kicker, title, description, action }: { kicker: string; title: string; description: string; action?: ReactNode }) {
  return <header className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
    <div className="max-w-3xl"><p className="eyebrow mb-3">{kicker}</p><h1 className="title">{title}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">{description}</p></div>{action}
  </header>
}
export function Loading() { return <div className="panel flex min-h-64 items-center justify-center gap-3 text-slate-400"><LoaderCircle className="animate-spin text-emerald" /> Loading verified artifacts…</div> }
export function ErrorState({ error }: { error: Error }) { return <div className="panel flex min-h-48 items-center justify-center gap-3 p-6 text-rose-300"><TriangleAlert /> {error.message}</div> }
export function Empty({ children }: { children: ReactNode }) { return <div className="panel p-8 text-center text-sm text-slate-400">{children}</div> }
export function Kpi({ label, value, note }: { label: string; value: string; note: string }) { return <article className="panel relative overflow-hidden p-5"><div className="absolute right-0 top-0 h-20 w-20 rounded-full bg-emerald/10 blur-2xl"/><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p><p className="mt-3 font-[Manrope] text-3xl font-bold tracking-tight">{value}</p><p className="mt-2 text-xs text-slate-500">{note}</p></article> }
