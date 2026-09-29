import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import MatchesView from '@/views/MatchesView.vue'

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/admin/users', name: 'admin-users', component: () => import('@/views/AdminUsersView.vue') },
    { path: '/knowledge', name: 'knowledge', component: () => import('@/views/KnowledgeBaseView.vue') },
    { path: '/agent', name: 'agent', component: () => import('@/views/AgentView.vue') },
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

    // Epic 6 球员单场分析与后续个人事件视频。
    { path: '/matches/:matchId/player-stats', name: 'player-stats', component: () => import('@/views/MatchPlayerStats.vue') },
    {
      path: '/matches/:matchId/goalkeeper-stats',
      name: 'goalkeeper-stats',
      redirect: (to) => ({ name: 'player-stats', params: { matchId: to.params.matchId } }),
    },
    { path: '/matches/:matchId/player-stats/:playerId', name: 'match-player-detail', component: () => import('@/views/MatchPlayerDetail.vue') },
    {
      path: '/matches/:matchId/goalkeeper-stats/:playerId',
      name: 'match-goalkeeper-detail',
      redirect: (to) => ({
        name: 'match-player-detail',
        params: { matchId: to.params.matchId, playerId: to.params.playerId },
      }),
    },

    { path: '/stage/:stageName', redirect: (to) => ({ name: 'matches', query: { stage: String(to.params.stageName) } }) },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
