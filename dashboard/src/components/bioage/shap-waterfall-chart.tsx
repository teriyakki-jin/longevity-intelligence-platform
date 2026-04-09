'use client'

import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { ShapFactor } from '@/lib/types/bioage'
import { COLORS, FEATURE_LABELS } from '@/lib/constants'

interface Props {
  agingFactors: ShapFactor[]
  protectiveFactors: ShapFactor[]
}

export function ShapWaterfallChart({ agingFactors, protectiveFactors }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const combined = [
      ...agingFactors.map(f => ({ ...f, impact: f.shap_impact_years })),
      ...protectiveFactors.map(f => ({ ...f, impact: -Math.abs(f.shap_impact_years) })),
    ].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact)).slice(0, 12)

    const margin = { top: 16, right: 80, bottom: 24, left: 140 }
    const width = svgRef.current.clientWidth || 500
    const barHeight = 26
    const height = combined.length * barHeight + margin.top + margin.bottom

    svgRef.current.setAttribute('height', String(height))

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const maxAbs = d3.max(combined, d => Math.abs(d.impact)) ?? 1
    const x = d3.scaleLinear()
      .domain([-maxAbs * 1.15, maxAbs * 1.15])
      .range([margin.left, width - margin.right])

    const y = d3.scaleBand()
      .domain(combined.map(d => d.feature))
      .range([margin.top, height - margin.bottom])
      .padding(0.25)

    const g = svg.append('g')

    // Zero line
    g.append('line')
      .attr('x1', x(0)).attr('x2', x(0))
      .attr('y1', margin.top).attr('y2', height - margin.bottom)
      .attr('stroke', COLORS.border).attr('stroke-width', 1)

    // Bars
    combined.forEach(d => {
      const color = d.impact > 0 ? COLORS.red : COLORS.green
      const barX = d.impact > 0 ? x(0) : x(d.impact)
      const barW = Math.abs(x(d.impact) - x(0))

      g.append('rect')
        .attr('x', barX)
        .attr('y', y(d.feature)!)
        .attr('width', barW)
        .attr('height', y.bandwidth())
        .attr('fill', color)
        .attr('opacity', 0.85)
        .attr('rx', 3)

      // Value label
      const labelX = d.impact > 0 ? x(d.impact) + 5 : x(d.impact) - 5
      const anchor = d.impact > 0 ? 'start' : 'end'
      g.append('text')
        .attr('x', labelX)
        .attr('y', y(d.feature)! + y.bandwidth() / 2 + 4)
        .attr('text-anchor', anchor)
        .attr('fill', color)
        .attr('font-size', '11px')
        .attr('font-family', 'monospace')
        .text(`${d.impact > 0 ? '+' : ''}${d.impact.toFixed(2)}yr`)
    })

    // Y axis labels
    combined.forEach(d => {
      g.append('text')
        .attr('x', margin.left - 8)
        .attr('y', y(d.feature)! + y.bandwidth() / 2 + 4)
        .attr('text-anchor', 'end')
        .attr('fill', COLORS.textMuted)
        .attr('font-size', '11px')
        .text(FEATURE_LABELS[d.feature] ?? d.feature)
    })

  }, [agingFactors, protectiveFactors])

  return (
    <div className="w-full">
      <div className="flex items-center gap-4 mb-3">
        <span className="flex items-center gap-1.5 text-xs text-[#8b949e]">
          <span className="w-3 h-3 rounded-sm bg-[#ff7b72] inline-block" />
          Accelerates aging
        </span>
        <span className="flex items-center gap-1.5 text-xs text-[#8b949e]">
          <span className="w-3 h-3 rounded-sm bg-[#3fb950] inline-block" />
          Protective
        </span>
      </div>
      <svg ref={svgRef} width="100%" className="overflow-visible" />
    </div>
  )
}
