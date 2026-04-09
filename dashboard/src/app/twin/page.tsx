'use client'

import { useState, useCallback } from 'react'
import { simulateTwin } from '@/lib/api/twin'
import type { SimulationResponse, InterventionRequest } from '@/lib/types/twin'
import { TrajectoryChart } from '@/components/twin/trajectory-chart'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'

const DEFAULT_INTERVENTIONS = {
  exercise_minutes_per_week: { current: 60, target: 200 },
  sleep_hours: { current: 6.5, target: 8.0 },
  drinks_per_week: { current: 7, target: 2 },
}

export default function TwinPage() {
  const [vals, setVals] = useState(DEFAULT_INTERVENTIONS)
  const [result, setResult] = useState<SimulationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateTarget = useCallback((key: keyof typeof vals, target: number) => {
    setVals(prev => ({ ...prev, [key]: { ...prev[key], target } }))
  }, [])

  const simulate = async () => {
    setLoading(true)
    setError(null)
    try {
      const interventions: InterventionRequest[] = Object.entries(vals).map(([variable, v]) => ({
        variable,
        current_value: v.current,
        target_value: v.target,
      }))
      const res = await simulateTwin({
        user_features: {},
        interventions,
        n_simulations: 500,
        time_horizon_years: 10,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-[#e6edf3]">Digital Twin Simulator</h2>
        <p className="text-[#8b949e] text-sm mt-1">See how lifestyle changes affect your biological age over 10 years.</p>
      </div>

      <div className="grid grid-cols-[340px_1fr] gap-6 items-start">
        <Card title="Lifestyle Interventions">
          <div className="flex flex-col gap-6">
            <Slider label="Exercise" value={vals.exercise_minutes_per_week.target}
              min={0} max={600} step={10} unit=" min/wk"
              onChange={v => updateTarget('exercise_minutes_per_week', v)} />
            <Slider label="Sleep" value={vals.sleep_hours.target}
              min={4} max={12} step={0.5} unit=" hrs"
              onChange={v => updateTarget('sleep_hours', v)} />
            <Slider label="Drinks" value={vals.drinks_per_week.target}
              min={0} max={30} unit="/wk"
              onChange={v => updateTarget('drinks_per_week', v)} />
            <Button onClick={simulate} disabled={loading} size="lg" className="w-full mt-2">
              {loading ? 'Simulating...' : 'Run Simulation'}
            </Button>
          </div>
        </Card>

        <div className="flex flex-col gap-5">
          {error && (
            <div className="bg-[#ff7b7222] border border-[#ff7b72] rounded-xl p-4 text-[#ff7b72] text-sm">{error}</div>
          )}
          {result && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <p className="text-[#8b949e] text-xs mb-1">Baseline Bio Age</p>
                  <p className="text-3xl font-bold text-[#e6edf3] font-mono">{result.baseline.biological_age.toFixed(1)}</p>
                </Card>
                <Card>
                  <p className="text-[#8b949e] text-xs mb-1">Projected Bio Age</p>
                  <p className="text-3xl font-bold text-[#3fb950] font-mono">{result.counterfactual.biological_age_mean.toFixed(1)}</p>
                </Card>
                <Card>
                  <p className="text-[#8b949e] text-xs mb-1">Years Saved</p>
                  <p className="text-3xl font-bold text-[#58a6ff] font-mono">
                    {Math.abs(result.counterfactual.bioage_change_mean).toFixed(1)}
                  </p>
                </Card>
              </div>
              <Card title="10-Year Trajectory">
                <TrajectoryChart trajectory={result.trajectory} />
              </Card>
              <Card title="Intervention Breakdown">
                <div className="flex flex-col gap-3">
                  {result.intervention_effects.map(eff => (
                    <div key={eff.intervention} className="flex items-center justify-between">
                      <span className="text-[#8b949e] text-sm">{eff.intervention.replace(/_/g, ' ')}</span>
                      <span className={`font-mono text-sm font-semibold ${eff.bioage_impact < 0 ? 'text-[#3fb950]' : 'text-[#ff7b72]'}`}>
                        {eff.bioage_impact > 0 ? '+' : ''}{eff.bioage_impact.toFixed(2)} yrs
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}
          {!result && !loading && (
            <Card>
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="text-4xl mb-4">🔮</div>
                <p className="text-[#8b949e] text-sm">Adjust sliders and click <span className="text-[#58a6ff]">Run Simulation</span>.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
