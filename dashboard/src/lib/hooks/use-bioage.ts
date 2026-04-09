'use client'

import { useState, useCallback } from 'react'
import { predictBioAge } from '../api/bioage'
import type { BioAgeRequest, BioAgeResponse } from '../types/bioage'
import { DEFAULT_LIFESTYLE } from '../constants'

const DEFAULT_REQUEST: BioAgeRequest = {
  blood_markers: {
    glucose_mg_dl: null, hba1c_pct: null, total_cholesterol_mg_dl: null,
    hdl_mg_dl: null, ldl_mg_dl: null, triglycerides_mg_dl: null,
    creatinine_mg_dl: null, alt_u_l: null, ast_u_l: null, albumin_g_dl: null,
    wbc_1000_ul: null, hemoglobin_g_dl: null, platelets_1000_ul: null,
    crp_mg_l: null, uric_acid_mg_dl: null,
  },
  demographics: {
    chronological_age: 35,
    sex: 'male',
    height_cm: null,
    weight_kg: null,
    waist_cm: null,
  },
  lifestyle: { ...DEFAULT_LIFESTYLE },
  include_explanation: true,
}

export function useBioAge() {
  const [formData, setFormData] = useState<BioAgeRequest>(DEFAULT_REQUEST)
  const [result, setResult] = useState<BioAgeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await predictBioAge(formData)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }, [formData])

  const updateBloodMarker = useCallback(
    (key: keyof BioAgeRequest['blood_markers'], value: number | null) => {
      setFormData(prev => ({
        ...prev,
        blood_markers: { ...prev.blood_markers, [key]: value },
      }))
    },
    [],
  )

  const updateDemographic = useCallback(
    (key: keyof BioAgeRequest['demographics'], value: number | string | null) => {
      setFormData(prev => ({
        ...prev,
        demographics: { ...prev.demographics, [key]: value },
      }))
    },
    [],
  )

  const updateLifestyle = useCallback(
    (key: keyof BioAgeRequest['lifestyle'], value: number | string) => {
      setFormData(prev => ({
        ...prev,
        lifestyle: { ...prev.lifestyle, [key]: value },
      }))
    },
    [],
  )

  return { formData, result, loading, error, submit, updateBloodMarker, updateDemographic, updateLifestyle }
}
