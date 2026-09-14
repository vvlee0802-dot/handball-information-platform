import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import MatchesView from '@/views/MatchesView.vue'

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/competitions', name: 'competitions', component: () => import('@/views/CompetitionsView.vue') },
    { path: '/competitions/:competitionId', name: 'competition-detail', component: () => import('@/views/CompetitionDetail.vue') },
    { path: '/matches', name: 'matches', component: MatchesView },
    { path: '/matches/:matchId', name: 'match-detail', component: () => import('@/views/MatchGameDetail.vue') },
    { path: '/matches/:matchId/upload', name: 'match-upload', component: () => import('@/views/FeatureBoundaryView.vue') },
    { path: '/matches/:matchId/analysis', name: 'match-analysis', component: () => import('@/views/FeatureBoundaryView.vue') },
    { path: '/teams', name: 'teams', component: () => import('@/views/TeamsView.vue') },
    { path: '/teams/:teamId', name: 'team-detail', component: () => import('@/views/TeamDetail.vue') },
    { path: '/players', name: 'players', component: () => import('@/views/PlayersView.vue') },
    { path: '/players/:playerId', name: 'player-detail', component: () => import('@/views/PlayerDetail.vue') },
    { path: '/venues', name: 'venues', component: () => import('@/views/VenuesView.vue') },
    { path: '/venues/:venueId', name: 'venue-detail', component: () => import('@/views/VenueDetail.vue') },

    // 保留现有的比赛球员统计原型，后续在 Phase 2 重新接入统一数据源。
    { path: '/matches/:matchId/player-stats', name: 'player-stats', component: () => import('@/views/MatchPlayerStats.vue') },
    { path: '/matches/:matchId/goalkeeper-stats', name: 'goalkeeper-stats', component: () => import('@/views/MatchGoalkeeperStats.vue') },
    { path: '/matches/:matchId/player-stats/:playerId', name: 'match-player-detail', component: () => import('@/views/MatchPlayerDetail.vue') },
    { path: '/matches/:matchId/goalkeeper-stats/:playerId', name: 'match-goalkeeper-detail', component: () => import('@/views/MatchGoalkeeperDetail.vue') },

    { path: '/stage/:stageName', redirect: (to) => ({ name: 'matches', query: { stage: String(to.params.stageName) } }) },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
