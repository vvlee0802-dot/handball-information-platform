// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import MatchesView from '@/views/MatchesView.vue'

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    hasPermission: () => true,
  }),
}))

vi.mock('@/services/matches', () => ({
  createMatch: vi.fn(),
  listMatches: vi.fn().mockResolvedValue([]),
  matchStatusLabels: {
    scheduled: '未开始',
    live: '进行中',
    completed: '已结束',
    cancelled: '已取消',
  },
}))

vi.mock('@/services/competitions', () => ({
  listCompetitions: vi.fn().mockResolvedValue([
    {
      id: 1,
      name: '测试赛事',
      season: '2026',
      stage: '决赛',
      status: 'active',
      created_at: '2026-10-03T00:00:00Z',
    },
  ]),
}))

vi.mock('@/services/teams', () => ({
  listTeams: vi.fn().mockResolvedValue([
    {
      id: 1,
      name: '队伍一',
      short_name: 'T1',
      city: '上海',
      country: '中国',
      gender: 'men',
      description: null,
      created_at: '2026-10-03T00:00:00Z',
    },
    {
      id: 2,
      name: '队伍二',
      short_name: 'T2',
      city: '北京',
      country: '中国',
      gender: 'men',
      description: null,
      created_at: '2026-10-03T00:00:00Z',
    },
  ]),
}))

vi.mock('@/services/venues', () => ({
  listVenues: vi.fn().mockResolvedValue([
    {
      id: 1,
      name: '测试场馆',
      city: '上海',
      address: '测试地址',
      capacity: 1000,
      description: null,
      created_at: '2026-10-03T00:00:00Z',
    },
  ]),
}))

describe('MatchesView', () => {
  it('opens the create match dialog when clicking 新增比赛', async () => {
    const wrapper = mount(MatchesView, {
      global: {
        stubs: {
          AppHeader: true,
          RouterLink: true,
        },
      },
    })

    await flushPromises()

    const createButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '新增比赛')

    expect(createButton).toBeDefined()
    await createButton!.trigger('click')

    expect(wrapper.get('[role="dialog"]').text()).toContain('新增比赛')
    expect(wrapper.get('#create-match-team-one').element.tagName).toBe('SELECT')
    expect(wrapper.get('#create-match-team-two').element.tagName).toBe('SELECT')
  })
})
