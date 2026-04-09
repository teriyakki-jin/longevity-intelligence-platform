import type { BioAgeResponse } from '@/lib/types/bioage'
import { Card } from '../ui/card'

interface Props {
  result: BioAgeResponse
}

export function BioAgeResultCard({ result }: Props) {
  const { biological_age, chronological_age, age_acceleration, percentile_for_age, confidence_interval, interpretation } = result
  const younger = age_acceleration < 0
  const accelColor = younger ? '#3fb950' : '#ff7b72'
  const accelSign = age_acceleration > 0 ? '+' : ''

  return (
    <Card>
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="text-[#8b949e] text-xs mb-1">Biological Age</p>
          <p className="text-5xl font-bold text-[#e6edf3] font-mono">{biological_age.toFixed(1)}</p>
          <p className="text-[#8b949e] text-sm mt-1">Chronological: {chronological_age} yrs</p>
        </div>
        <div className="text-right">
          <div
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-semibold"
            style={{ backgroundColor: `${accelColor}22`, color: accelColor }}
          >
            {accelSign}{age_acceleration.toFixed(1)} yrs
          </div>
          <p className="text-[#8b949e] text-xs mt-2">
            {younger ? 'Biologically younger' : 'Biologically older'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-5">
        <div className="bg-[#0d1117] rounded-lg p-3">
          <p className="text-[#8b949e] text-xs mb-1">Peer Percentile</p>
          <p className="text-[#e6edf3] font-semibold text-lg">
            {(100 - percentile_for_age).toFixed(0)}th
          </p>
          <p className="text-[#8b949e] text-xs">
            Healthier than {(100 - percentile_for_age).toFixed(0)}%
          </p>
        </div>
        <div className="bg-[#0d1117] rounded-lg p-3">
          <p className="text-[#8b949e] text-xs mb-1">95% CI</p>
          <p className="text-[#e6edf3] font-semibold text-lg font-mono">
            [{confidence_interval[0].toFixed(1)}, {confidence_interval[1].toFixed(1)}]
          </p>
          <p className="text-[#8b949e] text-xs">years</p>
        </div>
      </div>

      <p className="text-[#8b949e] text-xs leading-relaxed border-t border-[#21262d] pt-4">
        {interpretation}
      </p>
    </Card>
  )
}
