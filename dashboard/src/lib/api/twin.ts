import { apiFetch } from './client'
import type { SimulationRequest, SimulationResponse } from '../types/twin'

export function simulateTwin(request: SimulationRequest): Promise<SimulationResponse> {
  return apiFetch<SimulationResponse>('/twin/simulate', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
