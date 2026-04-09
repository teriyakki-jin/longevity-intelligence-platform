'use client'

import { useBioAge } from '@/lib/hooks/use-bioage'
import { BioAgeForm } from '@/components/bioage/bioage-form'
import { BioAgeResultCard } from '@/components/bioage/bioage-result-card'
import { ShapWaterfallChart } from '@/components/bioage/shap-waterfall-chart'
import { Card } from '@/components/ui/card'

export default function HomePage() {
  const { formData, result, loading, error, submit, updateBloodMarker, updateDemographic, updateLifestyle } = useBioAge()

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-[#e6edf3]">Biological Age Clock</h2>
        <p className="text-[#8b949e] text-sm mt-1">Enter your blood markers to predict your biological age.</p>
      </div>
      <div className="grid grid-cols-[380px_1fr] gap-6 items-start">
        <BioAgeForm
          formData={formData}
          loading={loading}
          onSubmit={submit}
          onUpdateBlood={updateBloodMarker}
          onUpdateDemo={updateDemographic}
          onUpdateLifestyle={updateLifestyle}
        />
        <div className="flex flex-col gap-5">
          {error && (
            <div className="bg-[#ff7b7222] border border-[#ff7b72] rounded-xl p-4 text-[#ff7b72] text-sm">{error}</div>
          )}
          {loading && (
            <Card>
              <div className="flex items-center gap-3 text-[#8b949e] text-sm py-8 justify-center">
                <div className="w-4 h-4 border-2 border-[#58a6ff] border-t-transparent rounded-full animate-spin" />
                Analyzing your biomarkers...
              </div>
            </Card>
          )}
          {result && !loading && (
            <>
              <BioAgeResultCard result={result} />
              {(result.top_aging_factors.length > 0 || result.top_protective_factors.length > 0) && (
                <Card title="Biomarker Impact on Aging">
                  <ShapWaterfallChart agingFactors={result.top_aging_factors} protectiveFactors={result.top_protective_factors} />
                </Card>
              )}
              <p className="text-[#484f58] text-xs">{result.disclaimer}</p>
            </>
          )}
          {!result && !loading && !error && (
            <Card>
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="text-4xl mb-4">🧬</div>
                <p className="text-[#8b949e] text-sm">Fill in your information and click <span className="text-[#58a6ff]">Predict Biological Age</span>.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
