'use client'

import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { TrajectoryPoint } from '@/lib/types/twin'
import { COLORS } from '@/lib/constants'

interface Props {
  trajectory: TrajectoryPoint[]
}

export function TrajectoryChart({ trajectory }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current || trajectory.length === 0) return

    const margin = { top: 20, right: 30, bottom: 40, left: 50 }
    const width = svgRef.current.clientWidth || 600
    const height = 240

    const svg = d3.select(svgRef.current).attr('height', height)
    svg.selectAll('*').remove()

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)
    const W = width - margin.left - margin.right
    const H = height - margin.top - margin.bottom

    const allVals = trajectory.flatMap(d => [d.bioage_baseline, d.bioage_counterfactual])
    const x = d3.scaleLinear().domain([0, d3.max(trajectory, d => d.year)!]).range([0, W])
    const y = d3.scaleLinear().domain([d3.min(allVals)! - 2, d3.max(allVals)! + 2]).range([H, 0])

    // Grid
    g.append('g').call(d3.axisLeft(y).ticks(5).tickSize(-W))
      .call(g => g.select('.domain').remove())
      .call(g => g.selectAll('.tick line').attr('stroke', COLORS.border).attr('stroke-dasharray', '2'))
      .call(g => g.selectAll('.tick text').attr('fill', COLORS.textMuted).attr('font-size', 11))

    g.append('g').attr('transform', `translate(0,${H})`)
      .call(d3.axisBottom(x).ticks(trajectory.length).tickFormat(d => `yr ${d}`))
      .call(g => g.select('.domain').attr('stroke', COLORS.border))
      .call(g => g.selectAll('.tick text').attr('fill', COLORS.textMuted).attr('font-size', 11))

    // Area between
    const area = d3.area<TrajectoryPoint>()
      .x(d => x(d.year))
      .y0(d => y(d.bioage_baseline))
      .y1(d => y(d.bioage_counterfactual))
      .curve(d3.curveMonotoneX)

    g.append('path').datum(trajectory).attr('d', area)
      .attr('fill', COLORS.green).attr('opacity', 0.12)

    // Lines
    const lineBase = d3.line<TrajectoryPoint>().x(d => x(d.year)).y(d => y(d.bioage_baseline)).curve(d3.curveMonotoneX)
    const lineCF = d3.line<TrajectoryPoint>().x(d => x(d.year)).y(d => y(d.bioage_counterfactual)).curve(d3.curveMonotoneX)

    g.append('path').datum(trajectory).attr('d', lineBase)
      .attr('stroke', COLORS.red).attr('stroke-width', 2).attr('fill', 'none').attr('stroke-dasharray', '5,3')

    g.append('path').datum(trajectory).attr('d', lineCF)
      .attr('stroke', COLORS.green).attr('stroke-width', 2.5).attr('fill', 'none')

    // Legend
    const leg = svg.append('g').attr('transform', `translate(${margin.left + W - 160},${margin.top})`)
    leg.append('line').attr('x1', 0).attr('x2', 20).attr('y1', 8).attr('y2', 8)
      .attr('stroke', COLORS.red).attr('stroke-width', 2).attr('stroke-dasharray', '5,3')
    leg.append('text').attr('x', 25).attr('y', 12).attr('fill', COLORS.textMuted).attr('font-size', 11).text('Current lifestyle')
    leg.append('line').attr('x1', 0).attr('x2', 20).attr('y1', 26).attr('y2', 26)
      .attr('stroke', COLORS.green).attr('stroke-width', 2.5)
    leg.append('text').attr('x', 25).attr('y', 30).attr('fill', COLORS.textMuted).attr('font-size', 11).text('After changes')

  }, [trajectory])

  return <svg ref={svgRef} width="100%" />
}
