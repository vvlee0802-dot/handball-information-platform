<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import * as THREE from 'three'
import { createHandballSurface, createLeatherGrain } from './handballSurface'

type ShowcaseItem = {
  label: string
  tone: string
}

const props = withDefaults(defineProps<{
  items?: ShowcaseItem[]
  showOrbit?: boolean
}>(), {
  items: () => [],
  showOrbit: true,
})
const container = ref<HTMLDivElement | null>(null)

let renderer: THREE.WebGLRenderer | null = null
let frameId: number | undefined
let resizeObserver: ResizeObserver | null = null
const geometries: THREE.BufferGeometry[] = []
const materials: THREE.Material[] = []
const textures: THREE.Texture[] = []

const accentColors: Record<string, string> = {
  blue: '#2563eb',
  cyan: '#14a9dc',
  violet: '#7c5cf0',
  orange: '#f18735',
  green: '#24b77f',
  red: '#ff4254',
}

const roundedRect = (
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) => {
  context.beginPath()
  context.roundRect(x, y, width, height, radius)
}

const createPanelTexture = (item: ShowcaseItem, index: number, back = false) => {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 640
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Canvas 2D context is unavailable')

  const accent = accentColors[item.tone] ?? '#2563eb'
  const background = context.createLinearGradient(0, 0, 1024, 640)
  background.addColorStop(0, back ? '#070c14' : '#101d31')
  background.addColorStop(1, '#060d18')
  context.fillStyle = background
  context.fillRect(0, 0, 1024, 640)

  const glow = context.createRadialGradient(190, 270, 20, 190, 270, 370)
  glow.addColorStop(0, `${accent}66`)
  glow.addColorStop(1, `${accent}00`)
  context.fillStyle = glow
  context.fillRect(0, 0, 1024, 640)

  context.fillStyle = '#070d17'
  context.fillRect(0, 0, 1024, 84)
  context.fillStyle = '#44536a'
  for (let dot = 0; dot < 3; dot += 1) {
    context.beginPath()
    context.arc(36 + dot * 24, 42, 6, 0, Math.PI * 2)
    context.fill()
  }
  context.fillStyle = '#7d8ba0'
  context.font = '700 17px Inter, system-ui, sans-serif'
  context.textAlign = 'right'
  context.fillText('HANDBALL DATA', 978, 49)

  if (back) {
    context.save()
    context.translate(512, 350)
    context.rotate(-0.04)
    context.textAlign = 'center'
    context.fillStyle = `${accent}2e`
    context.font = '800 250px Inter, system-ui, sans-serif'
    context.fillText(String(index + 1).padStart(2, '0'), 0, 82)
    context.fillStyle = '#b8c4d4'
    context.font = '800 42px Inter, system-ui, sans-serif'
    context.fillText('HANDBALL INTELLIGENCE', 0, 8)
    context.restore()
  } else {
    context.fillStyle = accent
    roundedRect(context, 72, 142, 122, 122, 28)
    context.fill()

    context.fillStyle = '#ffffff'
    context.textAlign = 'center'
    context.font = '800 54px "PingFang SC", "Microsoft YaHei", sans-serif'
    context.fillText(item.label.slice(0, 1), 133, 222)

    context.textAlign = 'left'
    context.fillStyle = `${accent}dd`
    context.font = '800 21px Inter, system-ui, sans-serif'
    context.fillText(String(index + 1).padStart(2, '0'), 235, 156)
    context.fillStyle = '#f7faff'
    context.font = '800 96px "PingFang SC", "Microsoft YaHei", sans-serif'
    context.fillText(item.label, 232, 248)

    const bars = [0.82, 0.58, 0.7]
    bars.forEach((length, barIndex) => {
      context.fillStyle = barIndex === 0 ? accent : '#29364a'
      roundedRect(context, 72, 330 + barIndex * 42, 310 * length, 16, 8)
      context.fill()
    })

    for (let card = 0; card < 3; card += 1) {
      context.fillStyle = card === 0 ? `${accent}24` : '#ffffff0b'
      roundedRect(context, 430 + card * 176, 330, 146, 130, 18)
      context.fill()
      context.strokeStyle = '#9fb5d126'
      context.lineWidth = 2
      context.stroke()
      context.fillStyle = card === 0 ? `${accent}cc` : '#718197'
      roundedRect(context, 452 + card * 176, 358, 70, 13, 7)
      context.fill()
      context.fillStyle = '#71819755'
      roundedRect(context, 452 + card * 176, 393, 100, 10, 5)
      context.fill()
    }
  }

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 8
  textures.push(texture)
  return texture
}

onMounted(() => {
  const host = container.value
  if (!host) return

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100)
  camera.position.set(0, 0.12, 7.8)
  camera.lookAt(0, -0.05, 0)

  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.08
  renderer.setClearColor(0x000000, 0)
  host.appendChild(renderer.domElement)

  const ballGeometry = createHandballSurface(1.568)
  const leatherGrain = createLeatherGrain()
  textures.push(leatherGrain)
  const ballMaterial = new THREE.MeshPhysicalMaterial({
    vertexColors: true,
    bumpMap: leatherGrain,
    bumpScale: 0.006,
    roughness: 0.78,
    metalness: 0,
    clearcoat: 0.08,
    clearcoatRoughness: 0.7,
  })
  geometries.push(ballGeometry)
  materials.push(ballMaterial)
  const ball = new THREE.Group()
  const seamGeometry = new THREE.SphereGeometry(1.565, 96, 64)
  const seamMaterial = new THREE.MeshStandardMaterial({ color: '#091c38', roughness: 0.9 })
  geometries.push(seamGeometry)
  materials.push(seamMaterial)
  ball.add(new THREE.Mesh(seamGeometry, seamMaterial), new THREE.Mesh(ballGeometry, ballMaterial))
  ball.rotation.set(-0.09, -0.35, 0.07)
  scene.add(ball)

  scene.add(new THREE.HemisphereLight(0xcde4ff, 0x020812, 2.15))
  const keyLight = new THREE.DirectionalLight(0xffe0c2, 4.6)
  keyLight.position.set(-3.6, 4.2, 5.5)
  scene.add(keyLight)
  const fillLight = new THREE.DirectionalLight(0x2f73ff, 3.4)
  fillLight.position.set(4.2, -0.5, 2.6)
  scene.add(fillLight)
  const rimLight = new THREE.PointLight(0x3080ff, 20, 13)
  rimLight.position.set(3.8, 1.2, -3)
  scene.add(rimLight)

  const orbitRoot = new THREE.Group()
  orbitRoot.rotation.set(-0.035, 0.25, -0.075)
  scene.add(orbitRoot)

  if (props.showOrbit) {
    const orbitGeometry = new THREE.TorusGeometry(2.78, 0.006, 8, 180)
    const orbitMaterial = new THREE.MeshBasicMaterial({ color: 0x5796ff, transparent: true, opacity: 0.26 })
    geometries.push(orbitGeometry)
    materials.push(orbitMaterial)
    const orbitLine = new THREE.Mesh(orbitGeometry, orbitMaterial)
    orbitLine.rotation.x = Math.PI / 2
    orbitRoot.add(orbitLine)

    const panelGeometry = new THREE.PlaneGeometry(1.92, 1.2)
    geometries.push(panelGeometry)
    const panelItems = props.items.slice(0, 6)
    panelItems.forEach((item, index) => {
      const angle = (index / panelItems.length) * Math.PI * 2
      const frontMaterial = new THREE.MeshBasicMaterial({ map: createPanelTexture(item, index), side: THREE.FrontSide })
      const backMaterial = new THREE.MeshBasicMaterial({ map: createPanelTexture(item, index, true), side: THREE.FrontSide })
      materials.push(frontMaterial, backMaterial)

      const panel = new THREE.Group()
      const front = new THREE.Mesh(panelGeometry, frontMaterial)
      front.position.z = 0.014
      panel.add(front)
      const back = new THREE.Mesh(panelGeometry, backMaterial)
      back.position.z = -0.014
      back.rotation.y = Math.PI
      panel.add(back)

      panel.position.set(Math.sin(angle) * 2.78, -0.2, Math.cos(angle) * 2.78)
      panel.rotation.y = angle
      orbitRoot.add(panel)
    })
  }

  const resize = () => {
    if (!renderer || !container.value) return
    const width = Math.max(1, container.value.clientWidth)
    const height = Math.max(1, container.value.clientHeight)
    renderer.setSize(width, height, false)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host)
  resize()

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  let lastTime = performance.now()
  const render = (now: number) => {
    frameId = window.requestAnimationFrame(render)
    const delta = Math.min((now - lastTime) / 1000, 0.05)
    lastTime = now
    if (!reducedMotion) {
      ball.rotation.y -= delta * 0.38
      orbitRoot.rotation.y += delta * 0.18
    }
    renderer?.render(scene, camera)
  }
  frameId = window.requestAnimationFrame(render)
})

onUnmounted(() => {
  if (frameId !== undefined) window.cancelAnimationFrame(frameId)
  resizeObserver?.disconnect()
  textures.forEach((texture) => texture.dispose())
  materials.forEach((material) => material.dispose())
  geometries.forEach((geometry) => geometry.dispose())
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss()
    renderer.domElement.remove()
  }
})
</script>

<template>
  <div ref="container" class="three-handball" aria-hidden="true"></div>
</template>

<style scoped>
.three-handball { width: 100%; height: 100%; }
.three-handball :deep(canvas) { display: block; width: 100%; height: 100%; }
</style>
