import { describe, expect, it } from 'vitest'
import { buildStationStats, connectedStationCount, edgeAppearance, filterEdges, topRelations } from './graph-utils'

const edges = [
  { source: 'A', target: 'B', weight: 50 },
  { source: 'B', target: 'C', weight: 20 },
  { source: 'C', target: 'A', weight: 19 },
]

describe('graph filtering and spatial summaries', () => {
  it('recalculates visible connections inclusively at the selected threshold', () => {
    expect(filterEdges(edges, 20)).toEqual(edges.slice(0, 2))
    expect(filterEdges(edges, 50)).toEqual(edges.slice(0, 1))
  })

  it('derives station statistics only from visible real edges', () => {
    const visible = filterEdges(edges, 20)
    const stats = buildStationStats(['A', 'B', 'C'], visible)
    expect(stats.get('A')).toEqual({ incoming: 0, outgoing: 1, trips: 50 })
    expect(stats.get('B')).toEqual({ incoming: 1, outgoing: 1, trips: 70 })
    expect(connectedStationCount(visible)).toBe(3)
  })

  it('orders frequent relations and scales strong links more visibly', () => {
    expect(topRelations(edges, 2).map(edge => edge.weight)).toEqual([50, 20])
    const weak = edgeAppearance(20, 20, 50)
    const strong = edgeAppearance(50, 20, 50)
    expect(strong.weight).toBeGreaterThan(weak.weight)
    expect(strong.opacity).toBeGreaterThan(weak.opacity)
  })
})
