'use client'

import { useState } from 'react'
import { Input } from '../ui/input'
import { Button } from '../ui/button'
import type { BioAgeRequest } from '@/lib/types/bioage'

interface Props {
  formData: BioAgeRequest
  loading: boolean
  onSubmit: () => void
  onUpdateBlood: (key: keyof BioAgeRequest['blood_markers'], value: number | null) => void
  onUpdateDemo: (key: keyof BioAgeRequest['demographics'], value: number | string | null) => void
  onUpdateLifestyle: (key: keyof BioAgeRequest['lifestyle'], value: number | string) => void
}

function parseNum(v: string): number | null {
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}

export function BioAgeForm({ formData, loading, onSubmit, onUpdateBlood, onUpdateDemo, onUpdateLifestyle }: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>({
    blood: true, body: false, lifestyle: false,
  })

  const toggle = (section: string) =>
    setOpen(prev => ({ ...prev, [section]: !prev[section] }))

  const bm = formData.blood_markers
  const dm = formData.demographics
  const ls = formData.lifestyle

  return (
    <div className="flex flex-col gap-4">
      {/* Demographics — always visible, required */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5">
        <h3 className="text-[#e6edf3] font-semibold text-sm mb-4">Demographics <span className="text-[#ff7b72] text-xs ml-1">required</span></h3>
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Age" unit="years" type="number" min={18} max={100}
            value={dm.chronological_age}
            onChange={e => onUpdateDemo('chronological_age', parseFloat(e.target.value))}
          />
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[#8b949e] font-medium">Sex</label>
            <select
              value={dm.sex}
              onChange={e => onUpdateDemo('sex', e.target.value)}
              className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>
        </div>
      </div>

      {/* Blood markers */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
        <button
          onClick={() => toggle('blood')}
          className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-[#21262d] transition-colors"
        >
          <span className="text-[#e6edf3] font-semibold text-sm">Blood Markers</span>
          <span className="text-[#8b949e] text-xs">{open.blood ? '▲' : '▼'}</span>
        </button>
        {open.blood && (
          <div className="px-5 pb-5 grid grid-cols-2 gap-3">
            {([
              ['glucose_mg_dl', 'Glucose', 'mg/dL'],
              ['hba1c_pct', 'HbA1c', '%'],
              ['total_cholesterol_mg_dl', 'Total Cholesterol', 'mg/dL'],
              ['hdl_mg_dl', 'HDL', 'mg/dL'],
              ['triglycerides_mg_dl', 'Triglycerides', 'mg/dL'],
              ['creatinine_mg_dl', 'Creatinine', 'mg/dL'],
              ['alt_u_l', 'ALT', 'U/L'],
              ['ast_u_l', 'AST', 'U/L'],
              ['albumin_g_dl', 'Albumin', 'g/dL'],
              ['wbc_1000_ul', 'WBC', '×10³/μL'],
              ['hemoglobin_g_dl', 'Hemoglobin', 'g/dL'],
              ['platelets_1000_ul', 'Platelets', '×10³/μL'],
              ['crp_mg_l', 'CRP', 'mg/L'],
              ['uric_acid_mg_dl', 'Uric Acid', 'mg/dL'],
            ] as const).map(([key, label, unit]) => (
              <Input
                key={key} label={label} unit={unit} type="number" optional
                placeholder="—"
                value={bm[key as keyof typeof bm] ?? ''}
                onChange={e => onUpdateBlood(key, parseNum(e.target.value))}
              />
            ))}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
        <button
          onClick={() => toggle('body')}
          className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-[#21262d] transition-colors"
        >
          <span className="text-[#e6edf3] font-semibold text-sm">Body Measurements</span>
          <span className="text-[#8b949e] text-xs">{open.body ? '▲' : '▼'}</span>
        </button>
        {open.body && (
          <div className="px-5 pb-5 grid grid-cols-2 gap-3">
            <Input label="Height" unit="cm" type="number" optional placeholder="—"
              value={dm.height_cm ?? ''} onChange={e => onUpdateDemo('height_cm', parseNum(e.target.value))} />
            <Input label="Weight" unit="kg" type="number" optional placeholder="—"
              value={dm.weight_kg ?? ''} onChange={e => onUpdateDemo('weight_kg', parseNum(e.target.value))} />
            <Input label="Waist" unit="cm" type="number" optional placeholder="—"
              value={dm.waist_cm ?? ''} onChange={e => onUpdateDemo('waist_cm', parseNum(e.target.value))} />
          </div>
        )}
      </div>

      {/* Lifestyle */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
        <button
          onClick={() => toggle('lifestyle')}
          className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-[#21262d] transition-colors"
        >
          <span className="text-[#e6edf3] font-semibold text-sm">Lifestyle</span>
          <span className="text-[#8b949e] text-xs">{open.lifestyle ? '▲' : '▼'}</span>
        </button>
        {open.lifestyle && (
          <div className="px-5 pb-5 grid grid-cols-2 gap-3">
            <Input label="Sleep" unit="hrs/night" type="number" step={0.5}
              value={ls.sleep_hours} onChange={e => onUpdateLifestyle('sleep_hours', parseFloat(e.target.value))} />
            <Input label="Drinks" unit="per week" type="number"
              value={ls.drinks_per_week} onChange={e => onUpdateLifestyle('drinks_per_week', parseFloat(e.target.value))} />
            <Input label="Exercise" unit="min/week" type="number"
              value={ls.exercise_minutes_per_week} onChange={e => onUpdateLifestyle('exercise_minutes_per_week', parseFloat(e.target.value))} />
            <Input label="Pack Years" type="number"
              value={ls.pack_years} onChange={e => onUpdateLifestyle('pack_years', parseFloat(e.target.value))} />
            <div className="flex flex-col gap-1 col-span-2">
              <label className="text-xs text-[#8b949e] font-medium">Smoking Status</label>
              <select
                value={ls.smoking_status}
                onChange={e => onUpdateLifestyle('smoking_status', e.target.value)}
                className="bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
              >
                <option value="never">Never</option>
                <option value="former">Former</option>
                <option value="current">Current</option>
              </select>
            </div>
          </div>
        )}
      </div>

      <Button onClick={onSubmit} disabled={loading} size="lg" className="w-full">
        {loading ? 'Analyzing...' : 'Predict Biological Age'}
      </Button>
    </div>
  )
}
