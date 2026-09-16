import type {
  AnalysisStatus,
  Competition,
  Match,
  MatchFilters,
  Player,
  Team,
  Venue,
  VideoStatus,
} from '@/types/domain'

export const competitions: Competition[] = [
  {
    id: 'paris-2024',
    name: '巴黎 2024 奥运会手球比赛',
    season: '2024',
    stage: '奥运会',
    status: '已结束',
    description: '巴黎奥运会手球项目，包含男子组和女子组的小组赛与淘汰赛。',
  },
  {
    id: 'world-2025',
    name: '2025 世界男子手球锦标赛',
    season: '2025',
    stage: '世界锦标赛',
    status: '已结束',
    description: '世界男子手球锦标赛示例赛事，用于展示跨赛事的信息关联。',
  },
]

export const teams: Team[] = [
  { id: 'denmark-men', name: '丹麦男子手球队', shortName: '丹麦', city: '哥本哈根', country: '丹麦', gender: '男子', description: '以快速攻防转换和稳定的后场进攻见长。' },
  { id: 'france-men', name: '法国男子手球队', shortName: '法国', city: '巴黎', country: '法国', gender: '男子', description: '拥有深厚的大赛经验和完整的攻防体系。' },
  { id: 'norway-men', name: '挪威男子手球队', shortName: '挪威', city: '奥斯陆', country: '挪威', gender: '男子', description: '比赛节奏鲜明，擅长利用转换进攻创造机会。' },
  { id: 'germany-men', name: '德国男子手球队', shortName: '德国', city: '柏林', country: '德国', gender: '男子', description: '强调身体对抗、阵地防守和战术纪律。' },
  { id: 'spain-men', name: '西班牙男子手球队', shortName: '西班牙', city: '马德里', country: '西班牙', gender: '男子', description: '擅长通过灵活跑位和细腻配合打开防线。' },
  { id: 'sweden-men', name: '瑞典男子手球队', shortName: '瑞典', city: '斯德哥尔摩', country: '瑞典', gender: '男子', description: '北欧传统强队，攻守结构平衡。' },
]

export const players: Player[] = [
  { id: 'den-1', name: '尼克拉斯·兰丁', number: 1, position: '守门员', teamId: 'denmark-men', birthDate: '1988-12-19', description: '丹麦队守门员，具备丰富的大赛经验。' },
  { id: 'den-7', name: '马格努斯·萨格斯楚普', number: 7, position: '中卫', teamId: 'denmark-men', birthDate: '1992-08-12', description: '负责组织进攻和连接前后场。' },
  { id: 'den-24', name: '米克尔·汉森', number: 24, position: '左后卫', teamId: 'denmark-men', birthDate: '1987-10-22', description: '具备远射和关键球处理能力。' },
  { id: 'fra-1', name: '文森特·热拉尔', number: 1, position: '守门员', teamId: 'france-men', birthDate: '1986-12-16', description: '法国队经验丰富的守门员。' },
  { id: 'fra-13', name: '尼古拉·卡拉巴蒂奇', number: 13, position: '中卫', teamId: 'france-men', birthDate: '1984-04-11', description: '能够组织阵地进攻并完成后场终结。' },
  { id: 'nor-5', name: '桑德尔·萨戈森', number: 5, position: '中卫', teamId: 'norway-men', birthDate: '1995-09-14', description: '挪威队后场核心球员。' },
  { id: 'ger-10', name: '尤里·克诺尔', number: 10, position: '中卫', teamId: 'germany-men', birthDate: '2000-05-09', description: '德国队年轻的组织型后场球员。' },
  { id: 'esp-6', name: '亚历克斯·杜伊舍巴耶夫', number: 6, position: '右后卫', teamId: 'spain-men', birthDate: '1992-12-17', description: '西班牙队右侧进攻的重要发起点。' },
]

export const venues: Venue[] = [
  { id: 'pierre-mauroy', name: '皮埃尔·莫鲁瓦球场', city: '里尔', address: '法国里尔都会区', capacity: 27000, description: '巴黎 2024 奥运会手球淘汰赛阶段比赛场馆。' },
  { id: 'unity-arena', name: '团结体育馆', city: '奥斯陆', address: '挪威奥斯陆', capacity: 15000, description: '2025 世界男子手球锦标赛比赛场馆之一。' },
]

export const matches: Match[] = [
  { id: 'paris-m-qf-den-nor', competitionId: 'paris-2024', date: '2024-08-07', startTime: '21:30', stage: '男子四分之一决赛', status: '已结束', teamAId: 'denmark-men', teamBId: 'norway-men', scoreA: 32, scoreB: 25, venueId: 'pierre-mauroy', videoStatus: 'ready', analysisStatus: 'completed' },
  { id: 'paris-m-final-fra-den', competitionId: 'paris-2024', date: '2024-08-11', startTime: '13:30', stage: '男子决赛', status: '已结束', teamAId: 'france-men', teamBId: 'denmark-men', scoreA: 26, scoreB: 39, venueId: 'pierre-mauroy', videoStatus: 'none', analysisStatus: 'not_started' },
  { id: 'world-m-sf-ger-den', competitionId: 'world-2025', date: '2025-01-31', startTime: '20:30', stage: '男子半决赛', status: '已结束', teamAId: 'germany-men', teamBId: 'denmark-men', scoreA: 26, scoreB: 40, venueId: 'unity-arena', videoStatus: 'processing', analysisStatus: 'processing' },
  { id: 'world-m-bronze-esp-fra', competitionId: 'world-2025', date: '2025-02-02', startTime: '15:00', stage: '男子季军赛', status: '已结束', teamAId: 'spain-men', teamBId: 'france-men', scoreA: 35, scoreB: 34, venueId: 'unity-arena', videoStatus: 'failed', analysisStatus: 'failed' },
]

export const videoStatusLabels: Record<VideoStatus, string> = {
  none: '未上传',
  uploaded: '已上传',
  processing: '处理中',
  ready: '可查看',
  failed: '处理失败',
}

export const analysisStatusLabels: Record<AnalysisStatus, string> = {
  not_started: '未开始',
  processing: '分析中',
  completed: '已完成',
  failed: '分析失败',
}

export const getCompetition = (id: string) => competitions.find((item) => item.id === id)
export const getTeam = (id: string) => teams.find((item) => item.id === id)
export const getPlayer = (id: string) => players.find((item) => item.id === id)
export const getVenue = (id: string) => venues.find((item) => item.id === id)
export const getMatch = (id: string) => matches.find((item) => item.id === id)

export const getTeamMatches = (teamId: string) => matches.filter((match) => match.teamAId === teamId || match.teamBId === teamId)
export const getCompetitionMatches = (competitionId: string) => matches.filter((match) => match.competitionId === competitionId)
export const getVenueMatches = (venueId: string) => matches.filter((match) => match.venueId === venueId)
export const getTeamPlayers = (teamId: string) => players.filter((player) => player.teamId === teamId)

export const filterMatches = (source: Match[], filters: MatchFilters) => {
  const keyword = filters.keyword.trim().toLocaleLowerCase('zh-CN')

  return source.filter((match) => {
    const competition = getCompetition(match.competitionId)
    const teamA = getTeam(match.teamAId)
    const teamB = getTeam(match.teamBId)
    const venue = getVenue(match.venueId)
    const searchable = [competition?.name, teamA?.name, teamB?.name, venue?.name, match.stage]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase('zh-CN')

    return (
      (!keyword || searchable.includes(keyword)) &&
      (!filters.competitionId || match.competitionId === filters.competitionId) &&
      (!filters.teamId || match.teamAId === filters.teamId || match.teamBId === filters.teamId) &&
      (!filters.venueId || match.venueId === filters.venueId) &&
      (!filters.stage || match.stage === filters.stage) &&
      (!filters.status || match.status === filters.status) &&
      (!filters.date || match.date === filters.date)
    )
  })
}
