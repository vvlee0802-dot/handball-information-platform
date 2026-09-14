import { describe, expect, it } from 'vitest'
import {
  competitions,
  filterMatches,
  getCompetition,
  getMatch,
  getTeam,
  getVenue,
  matches,
  players,
} from '@/data/handball'
import type { MatchFilters } from '@/types/domain'

const filters = (overrides: Partial<MatchFilters> = {}): MatchFilters => ({
  keyword: '',
  competitionId: '',
  teamId: '',
  venueId: '',
  stage: '',
  status: '',
  date: '',
  ...overrides,
})

describe('Epic 1 match discovery', () => {
  it('returns every match when filters are empty', () => {
    expect(filterMatches(matches, filters())).toHaveLength(matches.length)
  })

  it('finds matches when a team is either side', () => {
    const result = filterMatches(matches, filters({ teamId: 'denmark-men' }))
    expect(result.length).toBeGreaterThan(1)
    expect(result.every((match) => match.teamAId === 'denmark-men' || match.teamBId === 'denmark-men')).toBe(true)
  })

  it('combines competition, venue, stage and status filters', () => {
    const target = getMatch('paris-m-final-fra-den')!
    const result = filterMatches(matches, filters({
      competitionId: target.competitionId,
      venueId: target.venueId,
      stage: target.stage,
      status: target.status,
      date: target.date,
    }))
    expect(result.map((match) => match.id)).toEqual([target.id])
  })

  it('searches across event, teams, venue and stage', () => {
    expect(filterMatches(matches, filters({ keyword: '皮埃尔' })).length).toBeGreaterThan(0)
    expect(filterMatches(matches, filters({ keyword: '丹麦' })).length).toBeGreaterThan(0)
    expect(filterMatches(matches, filters({ keyword: '半决赛' })).length).toBeGreaterThan(0)
  })
})

describe('Epic 1 relationship integrity', () => {
  it('keeps every match linked to valid information entities', () => {
    for (const match of matches) {
      expect(getCompetition(match.competitionId)).toBeDefined()
      expect(getTeam(match.teamAId)).toBeDefined()
      expect(getTeam(match.teamBId)).toBeDefined()
      expect(getVenue(match.venueId)).toBeDefined()
    }
  })

  it('keeps every player linked to a valid team', () => {
    expect(players.every((player) => getTeam(player.teamId))).toBe(true)
  })

  it('provides at least one match for each competition', () => {
    expect(competitions.every((competition) => matches.some((match) => match.competitionId === competition.id))).toBe(true)
  })
})
