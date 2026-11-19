export type GraphEdge = { source: string; target: string; weight: number }

export type StationGraphStats = {
  incoming: number
  outgoing: number
  trips: number
}

export function filterEdges(edges: GraphEdge[], minimumTrips: number) {
  return edges.filter(edge => edge.weight >= minimumTrips)
}

export function buildStationStats(stationIds: string[], edges: GraphEdge[]) {
  const stats = new Map<string, StationGraphStats>(
    stationIds.map(id => [id, { incoming: 0, outgoing: 0, trips: 0 }]),
  )
  edges.forEach(edge => {
    const source = stats.get(edge.source)
    const target = stats.get(edge.target)
    if (source) {
      source.outgoing += 1
      source.trips += edge.weight
    }
    if (target) {
      target.incoming += 1
      target.trips += edge.weight
    }
  })
  return stats
}

export function connectedStationCount(edges: GraphEdge[]) {
  return new Set(edges.flatMap(edge => [edge.source, edge.target])).size
}

export function topRelations(edges: GraphEdge[], limit = 5) {
  return [...edges].sort((a, b) => b.weight - a.weight).slice(0, limit)
}

export function edgeAppearance(weight: number, minimum: number, maximum: number) {
  const safeMinimum = Math.max(1, minimum)
  const safeMaximum = Math.max(safeMinimum, maximum)
  const range = Math.log1p(safeMaximum) - Math.log1p(safeMinimum)
  const normalized = range === 0
    ? 1
    : Math.max(0, Math.min(1, (Math.log1p(weight) - Math.log1p(safeMinimum)) / range))
  return {
    opacity: 0.16 + normalized * 0.52,
    weight: 0.8 + normalized * 4.8,
  }
}
