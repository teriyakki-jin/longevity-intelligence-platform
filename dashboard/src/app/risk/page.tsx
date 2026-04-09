'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { apiFetch } from '@/lib/api/client'

interface RiskEntry {
  cause: string
  probability_5yr: number
  relative_risk: number
}

interface RiskResult {
  top_risks: RiskEntry[]
  five_year_survival_probability?: number
  ten_year_survival_probability?: number
}

const CAUSE_LABELS: Record<string, string> = {
  cardiovascular: 'Heart Disease',
  cancer: 'Cancer',
  respiratory: 'Respiratory',
  diabetes: 'Diabetes',
  accidents: 'Accidents',
  other: 'Other',
}

export default function RiskPage() {
  const [age, setAge] = useState(50)
  const [sex, setSex] = useState('male')
  const [result, setResult] = useState<RiskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const predict = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch<RiskResult>('/mortality/predict', {
        method: 'POST',
        body: JSON.stringify({
          blood_markers: {},
          demographics: { chronological_age: age, sex },
          lifestyle: { smoking_status: 'never', pack_years: 0, drinks_per_week: 3, exercise_minutes_per_week: 150, sleep_hours: 7.5 },
          include_explanation: false,
        }),
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }

  const maxProb = result ? Math.max(...result.top_risks.map(r => r.probability_5yr), 0.001) : 1

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-[#e6edf3]">Mortality Risk Profile</h2>
        <p className="text-[#8b949e] text-sm mt-1">Cause-specific mortality risk analysis.</p>
      </div>

      <div className="grid grid-cols-[300px_1fr] gap-6 items-start">
        <Card title="Profile">
          <div className="flex flex-col gap-4">
            <Input label="Age" unit="years" type="number" value={age}
              onChange={e => setAge(Number(e.target.value))} />
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#8b949e] font-medium">Sex</label>
              <select value={sex} onChange={e => setSex(e.target.value)}
                className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]">
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>
            <Button onClick={predict} disabled={loading} className="w-full">
              {loading ? 'Analyzing...' : 'Analyze Risk'}
            </Button>
          </div>
        </Card>

        <div className="flex flex-col gap-5">
          {error && <div className="bg-[#ff7b7222] border border-[#ff7b72] rounded-xl p-4 text-[#ff7b72] text-sm">{error}</div>}
          {result && (
            <Card title="Cause-Specific 5-Year Risk">
              <div className="flex flex-col gap-4 mt-2">
                {result.top_risks.map(r => {
                  const pct = r.probability_5yr * 100
                  const barW = (r.probability_5yr / maxProb) * 100
                  const color = r.relative_risk > 1.1 ? '#ff7b72' : r.relative_risk < 0.9 ? '#3fb950' : '#ffa657'
                  return (
                    <div key={r.cause}>
                      <div className="flex justify-between mb-1.5">
                        <span className="text-[#e6edf3] text-sm">{CAUSE_LABELS[r.cause] ?? r.cause}</span>
                        <span className="text-sm font-mono" style={{ color }}>
                          {pct.toFixed(2)}% <span className="text-[#8b949e] text-xs">(RR {r.relative_risk.toFixed(2)}x)</span>
                        </span>
                      </div>
                      <div className="h-2 bg-[#21262d] rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${barW}%`, backgroundColor: color, opacity: 0.85 }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          )}
          {!result && !loading && (
            <Card>
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="text-4xl mb-4">☠️</div>
                <p className="text-[#8b949e] text-sm">Enter your profile and click <span className="text-[#58a6ff]">Analyze Risk</span>.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
