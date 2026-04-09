import { apiFetch } from './client'
import type { BioAgeRequest, BioAgeResponse } from '../types/bioage'

export function predictBioAge(request: BioAgeRequest): Promise<BioAgeResponse> {
  return apiFetch<BioAgeResponse>('/bioage/predict', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
