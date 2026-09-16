import { apiRequest } from '@/services/http'

export interface VenueRecord {
  id: number
  name: string
  city: string
  address: string
  capacity: number
  description: string | null
  created_at: string
}

export interface VenueInput {
  name: string
  city: string
  address: string
  capacity: number
  description: string | null
}

export type VenueUpdate = Partial<VenueInput>

export const listVenues = () => apiRequest<VenueRecord[]>('/api/venues')
export const getVenue = (venueId: number) => apiRequest<VenueRecord>(`/api/venues/${venueId}`)
export const createVenue = (input: VenueInput) =>
  apiRequest<VenueRecord>('/api/venues', {
    method: 'POST',
    body: JSON.stringify(input),
  })
export const updateVenue = (venueId: number, input: VenueUpdate) =>
  apiRequest<VenueRecord>(`/api/venues/${venueId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
