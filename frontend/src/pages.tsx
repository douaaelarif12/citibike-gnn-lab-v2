import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { CircleMarker as LeafletCircleMarker } from 'leaflet'
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowUpRight, Download, MapPinned, Play, Search, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react'
import { api, Station } from './api'
import { Empty, ErrorState, Kpi, Loading, PageHeader } from './components'
import { buildStationStats, connectedStationCount, edgeAppearance, filterEdges, topRelations } from './graph-utils'

const chartTheme = { grid: 'var(--chart-grid)', axis: 'var(--chart-axis)', actual: '#75E3CF', model: '#10B981', naive: '#64748b' }
const tooltipStyle = { background: 'var(--tooltip-bg)', border: '1px solid var(--tooltip-border)', borderRadius: 12, color: 'var(--text-primary)' }
const fmt = (value: number, digits = 3) => value.toFixed(digits)

export function Overview() {
  const overview = useQuery({ queryKey: ['overview'], queryFn: api.overview })
  const predictions = useQuery({ queryKey: ['predictions'], queryFn: api.predictions })
  if (overview.isLoading || predictions.isLoading) return <Loading/>
  if (overview.error || predictions.error) return <ErrorState error={(overview.error || predictions.error) as Error}/>
  const bestRmse = [...overview.data!.comparisons].sort((a,b)=>a.rmse-b.rmse)[0]
  const gnn = overview.data!.comparisons.find(m=>m.model.includes('GCN'))
  return <><PageHeader kicker="Urban intelligence platform" title="Demand, decoded across space and time." description="A reproducible GCN–GRU research workspace for Jersey City mobility. Every KPI below comes from a persisted experiment artifact." action={<a className="flex items-center gap-2 rounded-xl bg-emerald px-4 py-3 text-sm font-bold text-graphite" href="/api/downloads/reproducible_comparison.csv"><Download size={17}/> Export metrics</a>}/>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Kpi label="Graph nodes" value={String(overview.data!.stations)} note="Evaluated stations"/><Kpi label="Test horizon" value={`${overview.data!.test_hours}h`} note="Untouched final split"/><Kpi label="Best RMSE" value={fmt(bestRmse.rmse)} note={bestRmse.model}/><Kpi label="GCN–GRU MAE" value={gnn?fmt(gnn.mae):'—'} note="Verified reference run"/></section>
    <section className="mt-5 grid gap-5 xl:grid-cols-[1.65fr_1fr]"><div className="panel p-5"><div className="mb-5"><p className="font-semibold">Network-wide demand</p><p className="text-xs text-slate-500">Final 108-hour test window</p></div><div className="h-[340px]"><ResponsiveContainer><AreaChart data={predictions.data}><defs><linearGradient id="demand" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={chartTheme.actual} stopOpacity={.35}/><stop offset="1" stopColor={chartTheme.actual} stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke={chartTheme.grid}/><XAxis dataKey="timestamp" hide/><YAxis stroke={chartTheme.axis}/><Tooltip contentStyle={tooltipStyle}/><Area isAnimationActive={false} dataKey="actual" stroke={chartTheme.actual} fill="url(#demand)" strokeWidth={2}/><Line isAnimationActive={false} dataKey="gcn_gru" stroke={chartTheme.model} dot={false}/></AreaChart></ResponsiveContainer></div></div>
    <div className="panel p-5"><p className="font-semibold">Scientific guardrails</p><div className="mt-5 space-y-4">{['Chronological train / validation / test','Scaler fitted on training inputs only','Training-only graph construction','Existing checkpoint preserved'].map((x,i)=><div key={x} className="flex gap-3 rounded-xl border border-white/5 bg-white/[.025] p-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-emerald/10 text-xs font-bold text-mint">0{i+1}</span><span className="text-sm text-slate-300">{x}</span></div>)}</div></div></section></>
}

function MapSelection({ station, markers }: { station?: Station; markers: MutableRefObject<Record<string, LeafletCircleMarker | null>> }) {
  const map = useMap()
  useEffect(() => {
    if (!station) return
    map.flyTo([station.lat, station.lng], Math.max(map.getZoom(), 15), { duration: 0.65 })
    const timer = window.setTimeout(() => markers.current[station.id]?.openPopup(), 700)
    return () => window.clearTimeout(timer)
  }, [map, markers, station])
  return null
}

export function GraphExplorer() {
  const graph = useQuery({ queryKey: ['graph'], queryFn: api.graph })
  const [minWeight, setMinWeight] = useState(20)
  const [stationQuery, setStationQuery] = useState('')
  const [selectedStationId, setSelectedStationId] = useState<string>()
  const [tileError, setTileError] = useState(false)
  const [tileLayerKey, setTileLayerKey] = useState(0)
  const markerRefs = useRef<Record<string, LeafletCircleMarker | null>>({})

  const nodes = useMemo(() => graph.data?.nodes ?? [], [graph.data?.nodes])
  const allEdges = useMemo(() => graph.data?.edges ?? [], [graph.data?.edges])
  const stationIds = useMemo(() => nodes.map(node => node.id), [nodes])
  const positions = useMemo(() => new Map(nodes.map(node => [node.id, [node.lat, node.lng] as [number, number]])), [nodes])
  const stationById = useMemo(() => new Map(nodes.map(node => [node.id, node])), [nodes])
  const visibleEdges = useMemo(() => filterEdges(allEdges, minWeight), [allEdges, minWeight])
  const allStationStats = useMemo(() => buildStationStats(stationIds, allEdges), [stationIds, allEdges])
  const visibleStationStats = useMemo(() => buildStationStats(stationIds, visibleEdges), [stationIds, visibleEdges])
  const frequentRelations = useMemo(() => topRelations(visibleEdges, 5), [visibleEdges])
  const selectedStation = selectedStationId ? stationById.get(selectedStationId) : undefined
  const visibleTrips = useMemo(() => visibleEdges.reduce((sum, edge) => sum + edge.weight, 0), [visibleEdges])
  const maxVisibleWeight = visibleEdges[0]?.weight ?? minWeight
  const stationMatches = useMemo(() => {
    const query = stationQuery.trim().toLocaleLowerCase()
    if (!query || selectedStation && stationQuery === `${selectedStation.id} — ${selectedStation.name}`) return []
    return nodes.filter(node => `${node.id} ${node.name}`.toLocaleLowerCase().includes(query)).slice(0, 8)
  }, [nodes, selectedStation, stationQuery])

  const chooseStation = (station: Station) => {
    setSelectedStationId(station.id)
    setStationQuery(`${station.id} — ${station.name}`)
  }

  if (graph.isLoading) return <Loading/>
  if (graph.error) return <ErrorState error={graph.error}/>

  return <>
    <PageHeader kicker="Spatial topology" title="Graph Explorer" description="Stations et relations observées dans les trajets Citi Bike d’avril 2026. Les statistiques, largeurs et transparences sont recalculées à partir du filtre actif."/>
    <section className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
      <div className="panel relative flex min-h-[58px] items-center gap-3 px-4">
        <Search className="shrink-0 text-mint" size={18}/>
        <label className="sr-only" htmlFor="station-search">Rechercher une station</label>
        <input id="station-search" value={stationQuery} onChange={event=>{setStationQuery(event.target.value);setSelectedStationId(undefined)}} placeholder="Rechercher par identifiant ou nom de station…" autoComplete="off" className="w-full bg-transparent text-sm outline-none placeholder:text-slate-500"/>
        {stationMatches.length > 0 && <div role="listbox" className="absolute left-0 right-0 top-[64px] z-[1100] overflow-hidden rounded-2xl border border-white/10 bg-[#122024]/95 p-2 shadow-2xl backdrop-blur">
          {stationMatches.map(station=><button role="option" aria-selected={station.id===selectedStationId} type="button" key={station.id} onClick={()=>chooseStation(station)} className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm text-slate-200 transition hover:bg-emerald/10 hover:text-mint"><span><b className="mr-2 text-mint">{station.id}</b>{station.name}</span><MapPinned size={15}/></button>)}
        </div>}
      </div>
      <div className="panel flex min-h-[58px] flex-wrap items-center gap-4 px-4 py-3">
        <label className="flex items-center gap-3 text-xs text-slate-300">Voyages minimums <input aria-label="Minimum trip count" className="w-32 accent-emerald" type="range" min="1" max="100" value={minWeight} onChange={event=>setMinWeight(Number(event.target.value))}/><b className="min-w-7 text-right text-mint">{minWeight}</b></label>
        <span aria-live="polite" className="border-l border-white/10 pl-4 text-xs text-slate-500">{visibleEdges.length.toLocaleString()} connexions</span>
      </div>
    </section>
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="panel relative h-[680px] overflow-hidden p-2">
        <MapContainer center={[40.72,-74.05]} zoom={13} className="graph-map h-full rounded-xl">
          <TileLayer key={tileLayerKey} attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} eventHandlers={{loading:()=>setTileError(false),tileerror:()=>setTileError(true)}}/>
          <MapSelection station={selectedStation} markers={markerRefs}/>
          {visibleEdges.map((edge,i)=>{
            const source = positions.get(edge.source), target = positions.get(edge.target)
            if (!source || !target) return null
            const appearance = edgeAppearance(edge.weight, minWeight, maxVisibleWeight)
            const isSelected = selectedStationId && (edge.source === selectedStationId || edge.target === selectedStationId)
            return <Polyline key={`${edge.source}-${edge.target}-${i}`} positions={[source,target]} pathOptions={{color:isSelected?'#75E3CF':'#10B981',opacity:selectedStationId?(isSelected?Math.min(.9,appearance.opacity+.16):.055):appearance.opacity,weight:isSelected?appearance.weight+1:appearance.weight}}/>
          })}
          {nodes.map(node=>{
            const total = allStationStats.get(node.id)!
            const visible = visibleStationStats.get(node.id)!
            const selected = node.id === selectedStationId
            return <CircleMarker ref={marker=>{markerRefs.current[node.id]=marker}} eventHandlers={{click:()=>chooseStation(node)}} key={node.id} center={[node.lat,node.lng]} radius={selected?9:Math.min(8,3+Math.log10(node.observations+1))} pathOptions={{color:selected?'#EFFCF7':'#75E3CF',fillColor:selected?'#75E3CF':'#10B981',fillOpacity:selected ? .95 : .8,weight:selected?2.5:1}}>
              <Popup><div className="station-popup"><strong>{node.name}</strong><span className="station-code">Station {node.id}</span><span>{node.lat.toFixed(5)}, {node.lng.toFixed(5)}</span><span>{node.observations.toLocaleString()} observations de coordonnées</span><span>{visible.outgoing} départs · {visible.incoming} arrivées visibles</span><span>{visible.trips.toLocaleString()} voyages liés au filtre</span><span className="station-popup-muted">Total mensuel : {total.outgoing + total.incoming} relations · {total.trips.toLocaleString()} voyages liés</span></div></Popup>
            </CircleMarker>
          })}
        </MapContainer>
        {tileError&&<div role="alert" aria-live="polite" className="absolute left-1/2 top-6 z-[1000] -translate-x-1/2 rounded-xl border border-rose-300/30 bg-[#111c1f]/95 px-4 py-3 text-sm text-rose-100 shadow-xl"><span>Le fond de carte n’a pas pu être chargé.</span><button type="button" className="ml-3 font-bold text-mint underline" onClick={()=>{setTileError(false);setTileLayerKey(value=>value+1)}}>Réessayer</button></div>}
        <div className="map-legend absolute bottom-10 left-5 z-[800] rounded-xl border border-white/10 bg-[#0b1115]/90 p-3 text-xs text-slate-200 shadow-xl backdrop-blur"><p className="mb-2 font-bold text-white">Légende</p><div><span className="mr-2 inline-block h-3 w-3 rounded-full border border-mint bg-emerald"/>Station Citi Bike</div><div className="mt-2 flex items-center"><span className="mr-2 inline-block h-px w-8 bg-emerald opacity-50"/>Relation moins fréquente</div><div className="mt-2 flex items-center"><span className="mr-2 inline-block h-[5px] w-8 bg-mint"/>Relation plus fréquente</div></div>
      </div>
      <aside className="space-y-4">
        <div className="panel p-5"><p className="eyebrow">Statistiques spatiales</p><div className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-1"><div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><p className="text-xs text-slate-500">Stations</p><p className="mt-1 text-2xl font-bold">{nodes.length.toLocaleString()}</p><p className="mt-1 text-[11px] text-slate-500">{connectedStationCount(visibleEdges).toLocaleString()} reliées au seuil</p></div><div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><p className="text-xs text-slate-500">Connexions visibles</p><p data-testid="visible-connection-count" className="mt-1 text-2xl font-bold text-mint">{visibleEdges.length.toLocaleString()}</p><p className="mt-1 text-[11px] text-slate-500">poids ≥ {minWeight} voyages</p></div><div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><p className="text-xs text-slate-500">Volume des relations</p><p className="mt-1 text-2xl font-bold">{visibleTrips.toLocaleString()}</p><p className="mt-1 text-[11px] text-slate-500">somme des fréquences visibles</p></div></div></div>
        <div className="panel p-5"><p className="eyebrow">Relations fréquentes</p><div className="mt-4 space-y-2">{frequentRelations.map((edge,index)=>{const source=stationById.get(edge.source),target=stationById.get(edge.target);return <button type="button" onClick={()=>source&&chooseStation(source)} key={`${edge.source}-${edge.target}`} className="w-full rounded-xl border border-white/5 bg-white/[.025] p-3 text-left transition hover:border-emerald/30 hover:bg-emerald/5"><div className="flex items-center justify-between gap-3"><span className="text-[11px] font-bold text-slate-500">#{index+1}</span><b className="text-sm text-mint">{edge.weight.toLocaleString()} voyages</b></div><p className="mt-2 truncate text-xs text-slate-300" title={`${source?.name ?? edge.source} → ${target?.name ?? edge.target}`}>{edge.source} · {source?.name ?? 'Station'} → {edge.target} · {target?.name ?? 'Station'}</p></button>})}{frequentRelations.length===0&&<p className="text-sm text-slate-500">Aucune relation ne satisfait ce seuil.</p>}</div></div>
      </aside>
    </section>
  </>
}

export function Forecasting() {
  const query = useQuery({ queryKey: ['predictions'], queryFn: api.predictions })
  const [windowHours, setWindowHours] = useState(108)
  const displayed = useMemo(() => (query.data ?? []).slice(-windowHours), [query.data, windowHours])
  const summary = useMemo(() => {
    if (!displayed.length) return { observed: 0, gcnError: 0, naiveError: 0 }
    return {
      observed: displayed.reduce((sum, row) => sum + row.actual, 0),
      gcnError: displayed.reduce((sum, row) => sum + Math.abs(row.gcn_gru - row.actual), 0) / displayed.length,
      naiveError: displayed.reduce((sum, row) => sum + Math.abs(row.naive - row.actual), 0) / displayed.length,
    }
  }, [displayed])
  if (query.isLoading) return <Loading/>; if (query.error) return <ErrorState error={query.error}/>
  return <><PageHeader kicker="Final test set" title="Demand Forecasting" description="Activité totale observée comparée au GCN–GRU et à la persistance sur des heures cibles identiques. L’artefact disponible est agrégé au niveau du réseau ; aucune série par station n’est simulée." action={<label className="panel flex items-center gap-3 px-4 py-3 text-xs text-slate-400">Période<select aria-label="Forecast period" value={windowHours} onChange={event=>setWindowHours(Number(event.target.value))} className="bg-transparent font-semibold text-mint outline-none"><option value={24}>24 dernières heures</option><option value={48}>48 dernières heures</option><option value={108}>Test complet · 108 h</option></select></label>}/><section className="mb-5 grid gap-4 md:grid-cols-3"><Kpi label="Activité observée" value={Math.round(summary.observed).toLocaleString()} note={`${displayed.length} heures affichées`}/><Kpi label="Erreur absolue agrégée GCN–GRU" value={fmt(summary.gcnError,1)} note="Moyenne sur les totaux horaires"/><Kpi label="Erreur absolue agrégée naïve" value={fmt(summary.naiveError,1)} note="Moyenne sur les totaux horaires"/></section><div className="panel p-5"><div className="h-[540px]"><ResponsiveContainer><LineChart data={displayed}><CartesianGrid stroke={chartTheme.grid}/><XAxis dataKey="timestamp" tick={{fill:chartTheme.axis,fontSize:11}} minTickGap={45}/><YAxis tick={{fill:chartTheme.axis,fontSize:11}}/><Tooltip contentStyle={tooltipStyle}/><Legend/><Line isAnimationActive={false} name="Observé" dataKey="actual" stroke={chartTheme.actual} dot={false} strokeWidth={2.3}/><Line isAnimationActive={false} name="GCN–GRU" dataKey="gcn_gru" stroke={chartTheme.model} dot={false}/><Line isAnimationActive={false} name="Persistance" dataKey="naive" stroke={chartTheme.naive} dot={false}/></LineChart></ResponsiveContainer></div></div></>
}

export function ModelComparison() {
  const query = useQuery({ queryKey: ['metrics'], queryFn: api.metrics })
  const comparison = useMemo(() => {
    const rows = query.data ?? []
    const bestMae = rows.length ? Math.min(...rows.map(row => row.mae)) : 0
    const bestRmse = rows.length ? Math.min(...rows.map(row => row.rmse)) : 0
    const gcn = rows.find(row => row.model.includes('GCN'))
    const naive = rows.find(row => row.model.toLocaleLowerCase().includes('naive'))
    return { bestMae, bestRmse, gcn, naive }
  }, [query.data])
  if (query.isLoading) return <Loading/>; if (query.error) return <ErrorState error={query.error}/>
  const rmseGain = comparison.gcn && comparison.naive ? comparison.naive.rmse - comparison.gcn.rmse : 0
  const maeGap = comparison.gcn && comparison.naive ? comparison.gcn.mae - comparison.naive.mae : 0
  return <><PageHeader kicker="Controlled comparison" title="Model Comparison" description="Comparaison fondée uniquement sur le pipeline reproductible autonome. Les résultats de notebooks utilisant d’autres découpages restent exclus."/><section className="mb-5 grid gap-4 md:grid-cols-2"><Kpi label="Gain RMSE du GCN–GRU" value={rmseGain>0?`−${fmt(rmseGain,4)}`:fmt(rmseGain,4)} note="Par rapport à la persistance"/><Kpi label="Écart MAE du GCN–GRU" value={maeGap>0?`+${fmt(maeGap,4)}`:fmt(maeGap,4)} note="La valeur positive favorise la baseline"/></section><div className="grid gap-5 xl:grid-cols-[1.1fr_1fr]"><div className="panel p-5"><div className="h-[390px]"><ResponsiveContainer><BarChart data={query.data}><CartesianGrid stroke={chartTheme.grid}/><XAxis dataKey="model" tick={{fill:chartTheme.axis,fontSize:12}}/><YAxis domain={[0,'auto']} tick={{fill:chartTheme.axis}}/><Tooltip contentStyle={tooltipStyle}/><Legend/><Bar isAnimationActive={false} dataKey="mae" name="MAE" fill={chartTheme.actual} radius={[6,6,0,0]}/><Bar isAnimationActive={false} dataKey="rmse" name="RMSE" fill={chartTheme.model} radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div></div><div className="panel overflow-hidden"><table className="w-full text-left text-sm"><thead className="border-b border-white/10 text-xs uppercase tracking-wider text-slate-500"><tr><th className="p-5">Modèle</th><th>MAE</th><th>RMSE</th></tr></thead><tbody>{query.data!.map(row=><tr key={row.model} className="border-b border-white/5"><td className="p-5 font-semibold">{row.model}</td><td><span>{fmt(row.mae)}</span>{row.mae===comparison.bestMae&&<span className="ml-2 rounded-full bg-emerald/10 px-2 py-1 text-[10px] font-bold text-mint">MEILLEUR</span>}</td><td><span>{fmt(row.rmse)}</span>{row.rmse===comparison.bestRmse&&<span className="ml-2 rounded-full bg-emerald/10 px-2 py-1 text-[10px] font-bold text-mint">MEILLEUR</span>}</td></tr>)}</tbody></table><div className="m-5 rounded-xl border border-mint/20 bg-mint/5 p-4 text-xs leading-5 text-slate-400"><ShieldCheck className="mb-2 text-mint" size={20}/>Le GCN–GRU réduit légèrement le RMSE, tandis que la persistance conserve le meilleur MAE. La complexité du modèle n’est donc pas présentée comme une victoire automatique.</div></div></div></>
}

export function StationAnalytics() {
  const stations = useQuery({ queryKey: ['stations'], queryFn: api.stations })
  const [selected, setSelected] = useState('HB106')
  const detail = useQuery({ queryKey: ['station',selected], queryFn:()=>api.station(selected), retry:false })
  const choices = useMemo(()=>{
    const all = stations.data ?? []
    const priority = new Map(['HB106','JC115','JC109'].map((id,index)=>[id,index]))
    return [...all].sort((a,b)=>(priority.get(a.id)??99)-(priority.get(b.id)??99)||a.name.localeCompare(b.name))
  },[stations.data])
  const evaluation = detail.data?.evaluation
  const errorBars = evaluation ? [{model:'GCN–GRU',mae:evaluation.gcn_gru_mae},{model:'Persistance',mae:evaluation.naive_mae}] : []
  const delta = evaluation ? evaluation.gcn_gru_mae - evaluation.naive_mae : undefined
  return <><PageHeader kicker="Local error inspection" title="Station Analytics" description="Analyse locale des stations présentes dans les artefacts de test. Les coordonnées, activités et erreurs affichées proviennent exclusivement du projet." action={<select aria-label="Station analytics selection" value={selected} onChange={event=>setSelected(event.target.value)} className="panel max-w-[340px] px-4 py-3 text-sm text-white outline-none">{choices.map(station=><option className="bg-panel" value={station.id} key={station.id}>{station.id} — {station.name}</option>)}</select>}/>{stations.isLoading||detail.isLoading?<Loading/>:detail.error?<Empty>Aucun artefact vérifié n’a été trouvé pour la station <b>{selected}</b>.</Empty>:<><section className="grid gap-4 md:grid-cols-3"><Kpi label="Station" value={selected} note={detail.data?.station?.name ?? 'Nom indisponible'}/><Kpi label="GCN–GRU MAE" value={evaluation?fmt(evaluation.gcn_gru_mae):'—'} note="Fenêtre de test finale"/><Kpi label="Persistance MAE" value={evaluation?fmt(evaluation.naive_mae):'—'} note={`${Math.round(evaluation?.activity ?? 0).toLocaleString()} mouvements observés`}/></section><section className="mt-5 grid gap-5 xl:grid-cols-[1fr_.8fr]"><div className="panel p-5"><p className="font-semibold">Erreur absolue moyenne locale</p><p className="mt-1 text-xs text-slate-500">Même station et même fenêtre de test</p><div className="mt-5 h-[310px]"><ResponsiveContainer><BarChart data={errorBars}><CartesianGrid stroke={chartTheme.grid}/><XAxis dataKey="model" tick={{fill:chartTheme.axis,fontSize:12}}/><YAxis tick={{fill:chartTheme.axis,fontSize:11}}/><Tooltip contentStyle={tooltipStyle}/><Bar isAnimationActive={false} dataKey="mae" name="MAE" fill={chartTheme.model} radius={[8,8,0,0]}/></BarChart></ResponsiveContainer></div></div><div className="panel p-6"><p className="eyebrow">Lecture locale</p><h2 className="mt-3 text-xl font-bold">{detail.data?.station?.name}</h2><p className="mt-2 text-sm text-slate-400">{detail.data?.station?`${detail.data.station.lat.toFixed(5)}, ${detail.data.station.lng.toFixed(5)}`:'Coordonnées indisponibles'}</p><div className="mt-6 rounded-xl border border-white/5 bg-white/[.025] p-4"><p className="text-xs text-slate-500">Écart GCN–GRU − persistance</p><p className={`mt-2 text-2xl font-bold ${delta!==undefined&&delta<=0?'text-mint':'text-slate-200'}`}>{delta===undefined?'—':`${delta>0?'+':''}${fmt(delta,3)}`}</p><p className="mt-2 text-xs leading-5 text-slate-400">{delta===undefined?'Comparaison indisponible.':delta<=0?'Le GCN–GRU obtient la plus faible MAE pour cette station.':'La persistance obtient la plus faible MAE pour cette station.'}</p></div></div></section></>}</>
}

export function Experiments() {
  const client = useQueryClient()
  const query = useQuery({queryKey:['experiments'],queryFn:api.experiments,refetchInterval:5000})
  const [config,setConfig]=useState({name:'gcn_gru_h12_huber',history:12,architecture:'gcn_gru',loss:'huber',graph:'weighted',epochs:20,patience:5,seed:42})
  const updateConfig = (key: string, value: string | number) => setConfig(current=>({...current,[key]:value}))
  const launch = useMutation({mutationFn:async()=>{const response=await fetch('/api/experiments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)});if(!response.ok)throw new Error(await response.text());return response.json()},onSuccess:()=>client.invalidateQueries({queryKey:['experiments']})})
  const fields = [
    {key:'history',label:'Historique',options:[[6,'6 h'],[12,'12 h'],[24,'24 h']]},
    {key:'architecture',label:'Architecture',options:[['gcn_gru','GCN–GRU'],['gru','GRU sans graphe']]},
    {key:'loss',label:'Perte',options:[['mse','MSE'],['mae','MAE'],['huber','Huber'],['peak_weighted','MSE pondérée pics']]},
    {key:'graph',label:'Graphe',options:[['binary','Binaire'],['weighted','Pondéré par trajets']]},
  ] as const
  return <><PageHeader kicker="Reproducible MLOps" title="Experiments Lab" description="Configurer un véritable entraînement CPU ou consulter les enregistrements JSONL terminés. Les tâches restent sérialisées pour protéger les ressources de la machine." action={<button onClick={()=>launch.mutate()} disabled={launch.isPending||!config.name.match(/^[a-zA-Z0-9_-]{3,64}$/)} className="flex items-center gap-2 rounded-xl bg-emerald px-4 py-3 text-sm font-bold text-graphite disabled:opacity-50"><Play size={16}/>{launch.isPending?'Soumission…':'Lancer l’expérience'}</button>}/><div className="grid gap-5 xl:grid-cols-[.9fr_1.1fr]"><div className="panel p-5"><label className="text-xs uppercase tracking-wider text-slate-500">Nom de l’expérience</label><input value={config.name} onChange={event=>updateConfig('name',event.target.value)} className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 outline-none focus:border-emerald"/><div className="mt-5 grid grid-cols-2 gap-3">{fields.map(field=><label key={field.key} className="text-xs text-slate-500">{field.label}<select value={config[field.key]} onChange={event=>updateConfig(field.key,field.key==='history'?Number(event.target.value):event.target.value)} className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white outline-none focus:border-emerald">{field.options.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>)}<label className="text-xs text-slate-500">Époques maximales<input type="number" min="1" max="500" value={config.epochs} onChange={event=>updateConfig('epochs',Number(event.target.value))} className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm outline-none focus:border-emerald"/></label><label className="text-xs text-slate-500">Patience<input type="number" min="1" max="50" value={config.patience} onChange={event=>updateConfig('patience',Number(event.target.value))} className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm outline-none focus:border-emerald"/></label><label className="text-xs text-slate-500">Seed<input type="number" min="0" value={config.seed} onChange={event=>updateConfig('seed',Number(event.target.value))} className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 p-3 text-sm outline-none focus:border-emerald"/></label></div><p className="mt-5 text-xs leading-5 text-slate-500">Le jeu de test reste réservé à l’évaluation finale. Un nouveau checkpoint versionné est créé ; le checkpoint historique n’est pas écrasé.</p>{launch.error&&<p className="mt-4 text-xs text-rose-300">{launch.error.message}</p>}</div><div className="panel p-5"><p className="mb-4 font-semibold">Historique des exécutions</p>{query.isLoading?<Loading/>:(!query.data?.completed.length&&!query.data?.tasks.length)?<Empty>Aucune expérience v2 n’a encore été exécutée.</Empty>:<div className="space-y-3">{[...(query.data?.tasks||[]),...(query.data?.completed||[])].map((run,i)=>{const entry=run as any;const metrics=entry.metrics;return <div key={String(entry.id||entry.created_at||i)} className="rounded-xl border border-white/5 bg-white/[.025] p-4"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-semibold">{String(entry.config?.name||entry.id||'Expérience')}</p><p className="mt-1 text-xs text-slate-500">{String(entry.created_at||'Artefact enregistré')}</p></div><span className="rounded-full bg-emerald/10 px-3 py-1 text-xs text-mint">{String(entry.status||'completed')}</span></div>{entry.config&&<p className="mt-3 text-xs text-slate-400">{entry.config.history} h · {entry.config.architecture} · {entry.config.loss} · graphe {entry.config.graph} · seed {entry.config.seed}</p>}{metrics&&<div className="mt-3 flex gap-4 border-t border-white/5 pt-3 text-xs"><span>MAE <b className="text-mint">{fmt(Number(metrics.MAE),4)}</b></span><span>RMSE <b className="text-mint">{fmt(Number(metrics.RMSE),4)}</b></span>{metrics.bias!==undefined&&<span>Biais <b className="text-mint">{fmt(Number(metrics.bias),4)}</b></span>}</div>}</div>})}</div>}</div></div></>
}

export function About() {
  return <><PageHeader kicker="Applied graph learning" title="About the Project" description="CitiBike GNN Lab v2 studies whether relational station structure improves short-horizon urban demand forecasting."/><div className="grid gap-5 lg:grid-cols-3"><article className="panel p-6 lg:col-span-2"><p className="eyebrow">Architecture</p><h2 className="mt-2 font-[Manrope] text-2xl font-bold">From raw trips to one-hour forecasts</h2><div className="mt-7 grid gap-3 md:grid-cols-4">{['Hourly aggregation','Graph convolution','Temporal GRU','Station forecast'].map((step,i)=><div key={step} className="relative rounded-xl border border-white/10 bg-white/[.025] p-4"><span className="text-xs font-bold text-emerald">0{i+1}</span><p className="mt-8 text-sm font-semibold">{step}</p>{i<3&&<ArrowUpRight className="absolute right-3 top-3 text-slate-600" size={17}/>}</div>)}</div><p className="mt-7 text-sm leading-7 text-slate-400">Station departures and arrivals are aggregated hourly. A graph convolution shares information across observed station links, while a GRU models temporal evolution. Calendar cycles are encoded with sine and cosine features. Hyperparameters are selected on validation data; the final test set remains isolated.</p></article><article className="panel p-6"><p className="eyebrow">Known limits</p><ul className="mt-5 space-y-4 text-sm leading-6 text-slate-400"><li>• One month and one city limit generalization.</li><li>• Peaks remain underestimated locally.</li><li>• The naive baseline has the best MAE.</li><li>• Weather and event covariates are absent.</li></ul></article></div></>
}
