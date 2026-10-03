<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'

import AppHeader from '@/components/AppHeader.vue'
import ThreeHandball from '@/components/ThreeHandball.vue'
import iconCompetition from '@/assets/figma/icon-competition.svg'
import iconKnowledge from '@/assets/figma/icon-knowledge.svg'
import iconMatch from '@/assets/figma/icon-match.svg'
import iconPlayer from '@/assets/figma/icon-player.svg'
import iconTeam from '@/assets/figma/icon-team.svg'
import iconVenue from '@/assets/figma/icon-venue.svg'
import { listCompetitions } from '@/services/competitions'
import { listMatches, matchStatusLabels, type MatchRecord } from '@/services/matches'
import { listPlayers } from '@/services/players'
import { listTeams, type TeamRecord } from '@/services/teams'
import { listVenues } from '@/services/venues'

const counts = reactive({ competitions: 0, matches: 0, teams: 0, players: 0, venues: 0 })
const matches = ref<MatchRecord[]>([])
const teams = ref<TeamRecord[]>([])
const motionSection = ref<HTMLElement | null>(null)
const scrollProgress = ref(0)
const reduceMotion = ref(false)
let animationFrame: number | undefined

const entries = [
  { to: '/competitions', label: '赛事', description: '管理赛制与阶段', icon: iconCompetition, tone: 'blue', rotate: -2 },
  { to: '/matches', label: '比赛', description: '视频、报告与事件', icon: iconMatch, tone: 'cyan', rotate: 7 },
  { to: '/teams', label: '球队', description: '名单与队伍资料', icon: iconTeam, tone: 'violet', rotate: 4 },
  { to: '/players', label: '球员', description: '个人数据与集锦', icon: iconPlayer, tone: 'orange', rotate: -4 },
  { to: '/venues', label: '场馆', description: '比赛地点信息', icon: iconVenue, tone: 'green', rotate: 5 },
  { to: '/knowledge', label: '知识库', description: '规则与资料问答', icon: iconKnowledge, tone: 'red', rotate: -6 },
]
const showcaseItems = entries.map(({ label, tone }) => ({ label, tone }))
const cardStarts = [0, 0.08, 0.24, 0.4, 0.56, 0.72]
const cardAngles = [-90, -30, 30, 90, 150, 210]

const sortedMatches = computed(() =>
  [...matches.value].sort((a, b) => `${b.match_date} ${b.start_time}`.localeCompare(`${a.match_date} ${a.start_time}`)),
)
const currentMatch = computed(() => sortedMatches.value[0] ?? null)
const recentMatches = computed(() => sortedMatches.value.slice(0, 5))
const teamNames = computed(() => new Map(teams.value.map((team) => [team.id, team.name])))
const revealedCardCount = computed(() => {
  if (reduceMotion.value) return entries.length
  return cardStarts.filter((start, index) => index === 0 || scrollProgress.value > start).length
})
const easeOutCubic = (value: number) => 1 - (1 - value) ** 3
const smoothStep = (value: number) => value * value * (3 - 2 * value)
const stageBallStyle = computed(() => {
  const progress = smoothStep(scrollProgress.value)
  return {
    '--ball-top': `${48 + progress * 38}%`,
    '--ball-scale': `${0.98 + progress * 0.58}`,
    '--ball-opacity': `${1 - progress * 0.25}`,
  }
})
const moduleCardStyle = (entry: (typeof entries)[number], index: number) => {
  const start = cardStarts[index] ?? 0
  const travelDuration = 0.14 + index * 0.025
  const rawProgress = index === 0 ? 1 : (scrollProgress.value - start) / travelDuration
  const localProgress = Math.min(1, Math.max(0, rawProgress))
  const eased = easeOutCubic(localProgress)
  const visible = index === 0 || localProgress > 0
  const targetAngle = cardAngles[index] ?? -90
  const angle = (-90 + (targetAngle + 90) * eased) * Math.PI / 180
  const x = Math.cos(angle) * 250
  const y = Math.sin(angle) * 180
  const tiltY = Math.abs(x) < 1 ? 0 : -Math.sign(x) * 17 * eased
  const tiltX = (y > 140 ? -6 : y < -140 ? 5 : 0) * eased
  const finalZIndex = index === 0 ? 7 : 6
  const zIndex = localProgress < 0.48 && index > 0 ? 7 : finalZIndex
  return {
    '--card-x': `${x}px`,
    '--card-y': `${y}px`,
    '--card-rotate': `${entry.rotate * eased}deg`,
    '--card-tilt-x': `${tiltX}deg`,
    '--card-tilt-y': `${tiltY}deg`,
    '--card-opacity': visible ? `${Math.min(1, localProgress * 5 || 1)}` : '0',
    '--card-scale': `${0.82 + eased * 0.18}`,
    '--card-z-index': `${zIndex}`,
  }
}
const teamName = (teamId: number) => teamNames.value.get(teamId) ?? '待定球队'
const score = (match: MatchRecord) => `${match.home_score ?? '—'} : ${match.away_score ?? '—'}`
const matchRoute = (match: MatchRecord) => ({ name: 'match-detail', params: { matchId: match.id } })

const updateScrollProgress = () => {
  animationFrame = undefined
  const section = motionSection.value
  if (!section || reduceMotion.value) {
    scrollProgress.value = reduceMotion.value ? 1 : 0
    return
  }
  const rect = section.getBoundingClientRect()
  const stickyOffset = window.innerWidth <= 760 ? 64 : 76
  const scrollableDistance = Math.max(1, section.offsetHeight - window.innerHeight)
  scrollProgress.value = Math.min(1, Math.max(0, (stickyOffset - rect.top) / scrollableDistance))
}

const scheduleScrollUpdate = () => {
  if (animationFrame !== undefined) return
  animationFrame = window.requestAnimationFrame(updateScrollProgress)
}

onMounted(async () => {
  reduceMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.addEventListener('scroll', scheduleScrollUpdate, { passive: true })
  window.addEventListener('resize', scheduleScrollUpdate)
  scheduleScrollUpdate()
  try {
    const [competitionRows, matchRows, teamRows, playerRows, venueRows] = await Promise.all([
      listCompetitions(), listMatches(), listTeams(), listPlayers(), listVenues(),
    ])
    matches.value = matchRows
    teams.value = teamRows
    Object.assign(counts, {
      competitions: competitionRows.length,
      matches: matchRows.length,
      teams: teamRows.length,
      players: playerRows.length,
      venues: venueRows.length,
    })
  } catch {
    /* 首页动画与导航不依赖接口数据。 */
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', scheduleScrollUpdate)
  window.removeEventListener('resize', scheduleScrollUpdate)
  if (animationFrame !== undefined) window.cancelAnimationFrame(animationFrame)
})
</script>

<template>
  <div class="page-shell home-page">
    <AppHeader />
    <main class="home-content">
      <section class="space-hero" aria-labelledby="home-title">
        <div class="hero-copy">
          <p>HANDBALL INFORMATION &amp; ANALYSIS</p>
          <h1 id="home-title">汇聚手球信息，读懂每一场比赛</h1>
          <span>集赛事资料、比赛数据、视频复盘和规则知识于一体，为教练员与球员提供清晰、可靠的比赛信息与分析依据。</span>
        </div>

        <div class="orbit-scene" aria-label="平台包含赛事、比赛、球队、球员、场馆和知识库六个模块">
          <div class="orbit-glow"></div>
          <div class="hero-three-ball"><ThreeHandball :items="showcaseItems" /></div>
          <div class="ball-shadow"></div>
        </div>

        <div class="scroll-cue" aria-hidden="true"><span></span><small>SCROLL</small></div>
      </section>

      <section
        ref="motionSection"
        class="motion-section"
        :class="{ 'reduce-motion': reduceMotion }"
        aria-labelledby="modules-title"
      >
        <div class="motion-stage">
          <div class="motion-copy">
            <p>EXPLORE THE PLATFORM</p>
            <h2 id="modules-title">六个板块，<br />构成完整的手球信息平台</h2>
            <small>通过赛事、比赛、球队、球员、场馆和知识库，快速查找与比赛相关的信息。</small>
            <span>{{ revealedCardCount }} / {{ entries.length }}</span>
          </div>

          <div class="stage-three-ball" :style="stageBallStyle">
            <ThreeHandball :show-orbit="false" />
          </div>
          <div class="module-ring" aria-label="平台功能入口">
            <RouterLink
              v-for="(entry, index) in entries"
              :key="entry.to"
              :to="entry.to"
              class="module-card"
              :class="[`tone-card-${entry.tone}`, { revealed: index < revealedCardCount }]"
              :style="moduleCardStyle(entry, index)"
              :aria-hidden="index >= revealedCardCount"
              :tabindex="index < revealedCardCount ? 0 : -1"
            >
              <span class="module-number">0{{ index + 1 }}</span>
              <span class="module-icon"><img :src="entry.icon" alt="" /></span>
              <div><h3>{{ entry.label }}</h3><p>{{ entry.description }}</p></div>
              <b>进入模块 ↗</b>
            </RouterLink>
          </div>

          <p class="motion-hint">继续滚动，让六个模块依次就位</p>
        </div>
      </section>

      <section class="dashboard-section" aria-labelledby="dashboard-title">
        <div class="dashboard-heading">
          <div><p>LIVE WORKSPACE</p><h2 id="dashboard-title">比赛工作台</h2></div>
          <span>{{ counts.matches }} 场比赛 · {{ counts.teams }} 支球队 · {{ counts.players }} 名球员</span>
        </div>

        <div class="dashboard-grid">
          <aside class="match-workbench">
            <template v-if="currentMatch">
              <div class="workbench-heading">
                <div><h3>当前比赛</h3><p>{{ currentMatch.match_date }} · {{ currentMatch.stage }}</p></div>
                <span class="status-badge" :class="currentMatch.status === 'completed' ? 'status-ready' : 'status-neutral'">
                  {{ matchStatusLabels[currentMatch.status] }}
                </span>
              </div>
              <p class="score-caption">{{ currentMatch.status === 'completed' ? '官方最终比分' : '当前比分' }}</p>
              <div class="workbench-score">{{ score(currentMatch) }}</div>
              <div class="workbench-teams">
                <strong>{{ teamName(currentMatch.home_team_id) }}</strong><span>VS</span><strong>{{ teamName(currentMatch.away_team_id) }}</strong>
              </div>
              <div class="workbench-actions">
                <RouterLink class="button button-primary" :to="matchRoute(currentMatch)">查看比赛</RouterLink>
                <RouterLink class="button dashboard-secondary" :to="{ name: 'player-stats', params: { matchId: currentMatch.id } }">球员分析</RouterLink>
              </div>
            </template>
            <div v-else class="workbench-empty">
              <h3>还没有比赛数据</h3>
              <p>添加比赛后，这里会显示最新比赛与快捷操作。</p>
              <RouterLink class="button button-primary" to="/matches">添加或查看比赛</RouterLink>
            </div>
          </aside>

          <div class="recent-panel">
            <div class="panel-heading"><h3>最近比赛</h3><RouterLink to="/matches">查看全部 →</RouterLink></div>
            <div v-if="recentMatches.length" class="recent-list">
              <RouterLink v-for="match in recentMatches" :key="match.id" :to="matchRoute(match)" class="match-row">
                <time>{{ match.match_date }}</time>
                <strong>{{ teamName(match.home_team_id) }}</strong>
                <b>{{ score(match) }}</b>
                <strong>{{ teamName(match.away_team_id) }}</strong>
                <span>{{ matchStatusLabels[match.status] }} →</span>
              </RouterLink>
            </div>
            <div v-else class="empty-match-card">暂无比赛数据，进入比赛页面创建第一场比赛。</div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.home-page { overflow-x: clip; color: white; background: #05080d; }
.home-content { position: relative; isolation: isolate; }
.home-content::before, .home-content::after { position: fixed; z-index: -1; inset: 0; pointer-events: none; content: ''; }
.home-content::before { opacity: .72; background-image: radial-gradient(circle at 12% 18%, rgba(105, 175, 255, .85) 0 1px, transparent 1.8px), radial-gradient(circle at 72% 28%, rgba(255,255,255,.72) 0 1px, transparent 1.6px), radial-gradient(circle at 38% 78%, rgba(124, 152, 255, .56) 0 1px, transparent 1.5px), radial-gradient(circle at 85% 74%, rgba(255,255,255,.48) 0 1.2px, transparent 1.8px); background-size: 147px 147px, 211px 211px, 263px 263px, 319px 319px; }
.home-content::after { background: radial-gradient(circle at 50% 30%, rgba(18, 91, 240, .15), transparent 36%), linear-gradient(180deg, rgba(4, 7, 12, .04), #05080d 88%); }
.space-hero { position: relative; display: grid; min-height: calc(100svh - 76px); place-items: center; overflow: hidden; }
.hero-copy { position: absolute; z-index: 5; top: 5%; left: 50%; width: min(720px, calc(100% - 40px)); text-align: center; transform: translateX(-50%); }
.hero-copy p, .motion-copy p, .dashboard-heading p { margin: 0 0 12px; color: #5f9dff; font-size: 12px; font-weight: 800; letter-spacing: .18em; }
.hero-copy h1 { margin: 0; font-size: clamp(28px, 3vw, 43px); font-weight: 680; line-height: 1.06; letter-spacing: -.045em; }
.hero-copy > span { display: block; margin-top: 17px; color: #8390a3; font-size: 13px; }
.orbit-scene { position: relative; width: min(920px, 78vw); height: min(650px, 72vh); margin-top: 14vh; perspective: 1200px; }
.orbit-glow { position: absolute; top: 50%; left: 50%; width: 46%; aspect-ratio: 1; border-radius: 50%; background: #125bf0; opacity: .14; filter: blur(76px); transform: translate(-50%, -50%); }
.hero-three-ball { position: absolute; z-index: 4; inset: 0; }
.ball-shadow { position: absolute; z-index: 1; top: 76%; left: 50%; width: 310px; height: 48px; border-radius: 50%; background: rgba(0, 72, 170, .4); filter: blur(26px); transform: translateX(-50%); }
.module-icon { display: grid; place-items: center; border-radius: 50%; }
.module-icon img { width: 17px; height: 17px; }
.scroll-cue { position: absolute; bottom: 26px; left: 50%; display: grid; justify-items: center; gap: 7px; color: #6f7b8d; transform: translateX(-50%); }
.scroll-cue span { width: 1px; height: 34px; background: linear-gradient(#5f9dff, transparent); animation: scroll-cue 1.7s ease-in-out infinite; }
.scroll-cue small { font-size: 9px; letter-spacing: .24em; }
.motion-section { position: relative; height: 520vh; }
.motion-stage { position: sticky; top: 76px; height: calc(100svh - 76px); overflow: hidden; background: linear-gradient(180deg, rgba(5, 8, 13, .12), rgba(5, 8, 13, .58)); }
.motion-copy { position: absolute; z-index: 12; top: 7%; left: max(32px, calc((100vw - 1320px) / 2)); max-width: 510px; }
.motion-copy h2 { margin: 0; font-size: clamp(26px, 3vw, 43px); line-height: 1.1; letter-spacing: -.04em; }
.motion-copy small { display: block; max-width: 460px; margin-top: 14px; color: #8390a3; font-size: 13px; font-weight: 400; line-height: 1.7; }
.motion-copy > span { display: inline-block; margin-top: 12px; color: #66758a; font-size: 12px; font-variant-numeric: tabular-nums; }
.stage-three-ball { position: absolute; z-index: 3; top: var(--ball-top); left: 50%; width: min(920px, 92vw); height: min(650px, 72vh); opacity: var(--ball-opacity); pointer-events: none; transform: translate(-50%, -50%) scale(var(--ball-scale)); transform-origin: center; will-change: top, transform, opacity; }
.stage-three-ball::after { position: absolute; inset: 5% 12% -5%; border-radius: 50%; background: linear-gradient(180deg, transparent 30%, rgba(3,9,18,.38)); content: ''; }
.module-ring { position: absolute; top: 54%; left: 50%; width: 1px; height: 1px; }
.module-card { position: absolute; z-index: var(--card-z-index); top: 0; left: 0; display: grid; width: 224px; min-height: 132px; grid-template-columns: auto 1fr; grid-template-rows: auto 1fr auto; gap: 8px 12px; padding: 16px; overflow: hidden; border: 1px solid rgba(156, 185, 226, .22); border-radius: 18px; color: white; background: linear-gradient(145deg, rgba(20, 32, 50, .96), rgba(7, 13, 23, .94)); box-shadow: 0 22px 48px rgba(0,0,0,.4); opacity: var(--card-opacity); pointer-events: none; transform: perspective(1200px) translate(-50%, -50%) translate(var(--card-x), var(--card-y)) rotateX(var(--card-tilt-x)) rotateY(var(--card-tilt-y)) rotateZ(var(--card-rotate)) scale(var(--card-scale)); transform-style: preserve-3d; transition: border-color .2s ease, box-shadow .2s ease; will-change: transform, opacity; backdrop-filter: blur(16px); }
.module-card::before { position: absolute; inset: 0 auto 0 0; width: 3px; background: #125bf0; content: ''; }
.module-card.revealed { pointer-events: auto; }
.module-card:hover { z-index: 12; border-color: rgba(95, 157, 255, .72); box-shadow: 0 28px 62px rgba(0,0,0,.5); transform: perspective(1200px) translate(-50%, -50%) translate(var(--card-x), var(--card-y)) translateY(-7px) rotateX(var(--card-tilt-x)) rotateY(var(--card-tilt-y)) rotateZ(var(--card-rotate)) scale(calc(var(--card-scale) + .025)); }
.module-number { color: #65758c; font-size: 10px; font-weight: 800; letter-spacing: .14em; }
.module-icon { width: 38px; height: 38px; justify-self: end; background: #125bf0; }
.module-card > div { grid-column: 1 / -1; }
.module-card h3 { margin: 0 0 4px; font-size: 21px; }
.module-card p { margin: 0; color: #93a0b4; font-size: 12px; }
.module-card b { grid-column: 1 / -1; color: #72a9ff; font-size: 11px; }
.tone-card-red::before, .tone-card-red .module-icon { background: #ff3346; }.tone-card-green::before, .tone-card-green .module-icon { background: #19a974; }.tone-card-orange::before, .tone-card-orange .module-icon { background: #ed7b2d; }.tone-card-violet::before, .tone-card-violet .module-icon { background: #7b5cf0; }.tone-card-cyan::before, .tone-card-cyan .module-icon { background: #078bb7; }
.motion-hint { position: absolute; z-index: 8; right: max(28px, calc((100vw - 1320px) / 2)); bottom: 28px; margin: 0; color: #67758a; font-size: 11px; letter-spacing: .08em; }
.motion-section.reduce-motion { height: calc(100svh - 76px); }
.dashboard-section { position: relative; z-index: 10; width: min(1360px, calc(100% - 48px)); min-height: 720px; margin: 0 auto; padding: 100px 0 80px; }
.dashboard-section::before { position: absolute; z-index: -1; inset: 44px -32px 28px; border: 1px solid rgba(129, 161, 205, .13); border-radius: 32px; background: rgba(9, 16, 27, .9); box-shadow: 0 30px 90px rgba(0,0,0,.3); content: ''; backdrop-filter: blur(20px); }
.dashboard-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
.dashboard-heading h2 { margin: 0; font-size: 38px; letter-spacing: -.04em; }
.dashboard-heading > span { color: #8290a5; font-size: 12px; }
.dashboard-grid { display: grid; grid-template-columns: minmax(340px, .78fr) minmax(0, 1.42fr); gap: 18px; }
.match-workbench, .recent-panel { min-height: 390px; padding: 26px; border: 1px solid rgba(144, 174, 216, .15); border-radius: 22px; background: rgba(12, 22, 36, .9); }
.workbench-heading, .panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.match-workbench h3, .recent-panel h3 { margin: 0; font-size: 21px; }
.workbench-heading p, .workbench-empty p { margin: 5px 0 0; color: #8290a5; }
.score-caption { margin: 42px 0 8px; color: #77869a; font-size: 11px; }
.workbench-score { font-size: 52px; font-weight: 780; line-height: 1; letter-spacing: -.05em; }
.workbench-teams { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; margin-top: 15px; }
.workbench-teams strong:last-child { text-align: right; }.workbench-teams span { color: #607086; font-size: 10px; }
.workbench-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 48px; }
.dashboard-secondary { border: 1px solid rgba(117,153,204,.3); color: white; background: #13243a; }
.workbench-empty { display: grid; height: 100%; align-content: center; gap: 16px; }
.panel-heading { align-items: center; margin-bottom: 15px; }.panel-heading a { color: #75aaff; font-size: 12px; font-weight: 700; }
.recent-list { border-top: 1px solid rgba(141,171,213,.13); }
.match-row { display: grid; grid-template-columns: 92px minmax(90px, 1fr) auto minmax(90px, 1fr) 86px; align-items: center; gap: 13px; min-height: 61px; border-bottom: 1px solid rgba(141,171,213,.11); color: white; }
.match-row time, .match-row span { color: #7e8da2; font-size: 11px; }.match-row strong { font-size: 13px; }.match-row strong:nth-of-type(2) { text-align: right; }.match-row b { color: #75aaff; font-size: 17px; white-space: nowrap; }.match-row span { color: #6fa7ff; text-align: right; }
.empty-match-card { display: grid; min-height: 290px; place-items: center; color: #7e8da2; text-align: center; }
@keyframes scroll-cue { 0%,100% { opacity: .25; transform: scaleY(.65); transform-origin: top; } 50% { opacity: 1; transform: scaleY(1); } }
@media (max-width: 980px) {
  .hero-copy { top: 5%; }.orbit-scene { width: 880px; transform: scale(.82); }.module-card { width: 196px; }
  .module-card { transform: perspective(1200px) translate(-50%, -50%) translate(calc(var(--card-x) * .78), calc(var(--card-y) * .82)) rotateX(var(--card-tilt-x)) rotateY(var(--card-tilt-y)) rotateZ(var(--card-rotate)) scale(var(--card-scale)); }
  .module-card:hover { transform: perspective(1200px) translate(-50%, -50%) translate(calc(var(--card-x) * .78), calc(var(--card-y) * .82)) translateY(-5px) rotateX(var(--card-tilt-x)) rotateY(var(--card-tilt-y)) rotateZ(var(--card-rotate)) scale(calc(var(--card-scale) + .025)); }
  .dashboard-grid { grid-template-columns: 1fr; }
}
@media (max-width: 680px) {
  .space-hero { min-height: calc(100svh - 64px); }.hero-copy { top: 4%; left: 50%; }.hero-copy h1 { font-size: 29px; }
  .orbit-scene { width: 720px; height: 500px; margin-top: 18vh; transform: scale(.62); }
  .motion-section { height: 430vh; }.motion-stage { top: 64px; height: calc(100svh - 64px); }.motion-copy { top: 5%; left: 20px; right: 20px; }.motion-copy h2 { max-width: 340px; font-size: 27px; }
  .stage-three-ball { width: 720px; height: 500px; }.module-ring { top: 55%; }
  .module-card { width: 142px; min-height: 105px; padding: 11px; border-radius: 14px; }.module-card h3 { font-size: 17px; }.module-card p { font-size: 10px; }.module-card b { display: none; }.module-icon { width: 30px; height: 30px; }.module-number { font-size: 8px; }
  .module-card { transform: perspective(900px) translate(-50%, -50%) translate(calc(var(--card-x) * .48), calc(var(--card-y) * .66)) rotateX(var(--card-tilt-x)) rotateY(var(--card-tilt-y)) rotateZ(var(--card-rotate)) scale(var(--card-scale)); }
  .module-card:hover { z-index: 8; transform: perspective(900px) translate(-50%, -50%) translate(calc(var(--card-x) * .48), calc(var(--card-y) * .66)) translateY(-4px) rotateX(var(--card-tilt-x)) rotateY(var(--card-tilt-y)) rotateZ(var(--card-rotate)) scale(calc(var(--card-scale) + .02)); }.motion-hint { right: 20px; bottom: 18px; }.motion-section.reduce-motion { height: calc(100svh - 64px); }
  .dashboard-section { width: calc(100% - 28px); padding: 72px 0 52px; }.dashboard-section::before { inset: 26px -8px 16px; border-radius: 22px; }.dashboard-heading { align-items: flex-start; flex-direction: column; }.dashboard-heading h2 { font-size: 31px; }
  .match-workbench, .recent-panel { min-height: auto; padding: 20px; }.match-row { grid-template-columns: 68px 1fr auto; padding: 12px 0; }.match-row strong:nth-of-type(2), .match-row span { display: none; }.workbench-actions { margin-top: 34px; }
}
@media (prefers-reduced-motion: reduce) { .scroll-cue span { animation-play-state: paused; }.module-card { transition: none; } }
</style>
