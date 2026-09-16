export type MatchStatus = '未开始' | '进行中' | '已结束'
export type CompetitionStatus = '进行中' | '已结束'
export type VideoStatus = 'none' | 'uploaded' | 'processing' | 'ready' | 'failed'
export type AnalysisStatus = 'not_started' | 'processing' | 'completed' | 'failed'

export interface Competition {
  id: string
  name: string
  season: string
  stage: string
  status: CompetitionStatus
  description: string
}

export interface Team {
  id: string
  name: string
  shortName: string
  city: string
  country: string
  gender: '男子' | '女子'
  description: string
}

export interface Player {
  id: string
  name: string
  number: number
  position: string
  teamId: string
  birthDate: string
  description: string
}

export interface Venue {
  id: string
  name: string
  city: string
  address: string
  capacity: number
  description: string
}

export interface Match {
  id: string
  competitionId: string
  date: string
  startTime: string
  stage: string
  status: MatchStatus
  teamAId: string
  teamBId: string
  scoreA: number | null
  scoreB: number | null
  venueId: string
  videoStatus: VideoStatus
  analysisStatus: AnalysisStatus
}

export interface MatchFilters {
  keyword: string
  competitionId: string
  teamId: string
  venueId: string
  stage: string
  status: MatchStatus | ''
  date: string
}
