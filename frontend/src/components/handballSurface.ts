import * as THREE from 'three'

// Truncate an icosahedron: 12 pentagons and 20 hexagons, projected onto a sphere.
// Building the leather panels in 3D avoids texture seams and distortion at the poles.
export function createHandballSurface(radius: number) {
  const source = new THREE.IcosahedronGeometry(1, 0)
  const sourcePositions = source.getAttribute('position')
  const vertices: THREE.Vector3[] = []
  const faces: number[][] = []
  const neighbors: Set<number>[] = []
  for (let offset = 0; offset < sourcePositions.count; offset += 3) {
    const face: number[] = []
    for (let corner = 0; corner < 3; corner += 1) {
      const point = new THREE.Vector3().fromBufferAttribute(sourcePositions, offset + corner).normalize()
      let index = vertices.findIndex((vertex) => vertex.distanceToSquared(point) < 1e-8)
      if (index < 0) {
        index = vertices.length
        vertices.push(point)
        neighbors.push(new Set())
      }
      face.push(index)
    }
    face.forEach((index) => face.forEach((other) => {
      if (index !== other) neighbors[index]!.add(other)
    }))
    faces.push(face)
  }
  source.dispose()

  const truncate = (from: number, to: number) => vertices[from]!.clone()
    .multiplyScalar(2).add(vertices[to]!).normalize()
  const polygons = faces.map(([a, b, c]) => [
    truncate(a!, b!), truncate(b!, a!), truncate(b!, c!),
    truncate(c!, b!), truncate(c!, a!), truncate(a!, c!),
  ])
  vertices.forEach((_, index) => {
    polygons.push([...neighbors[index]!].map((neighbor) => truncate(index, neighbor)))
  })

  const positions: number[] = []
  const colors: number[] = []
  const uvs: number[] = []
  const indices: number[] = []
  const warmDirection = new THREE.Vector3(-0.65, 0.3, 0.7).normalize()

  polygons.forEach((polygon, panelIndex) => {
    const center = polygon.reduce((sum, point) => sum.add(point), new THREE.Vector3()).normalize()
    const tangent = new THREE.Vector3().crossVectors(
      Math.abs(center.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0), center,
    ).normalize()
    const bitangent = new THREE.Vector3().crossVectors(center, tangent).normalize()
    polygon.sort((a, b) => Math.atan2(a.dot(bitangent), a.dot(tangent))
      - Math.atan2(b.dot(bitangent), b.dot(tangent)))
    // A narrow inset exposes the recessed dark shell between adjacent panels.
    const corners = polygon.map((corner) => corner.clone().lerp(center, 0.012).normalize())
    const warm = center.dot(warmDirection) > 0.48
    const color = new THREE.Color(warm ? '#e77c49' : '#225db7')
    color.multiplyScalar(0.94 + (panelIndex % 4) * 0.025)
    const edgeSamples = 10
    const ringCount = 14
    const perimeter = corners.length * edgeSamples
    const base = positions.length / 3
    const appendVertex = (direction: THREE.Vector3, fraction: number) => {
      // Subtle padding rolls down toward the stitched edge of each leather panel.
      const padding = 0.012 * (1 - Math.pow(fraction, 8))
      const point = direction.clone().multiplyScalar(radius + padding)
      positions.push(point.x, point.y, point.z)
      colors.push(color.r, color.g, color.b)
      uvs.push(direction.dot(tangent) * 7, direction.dot(bitangent) * 7)
    }
    appendVertex(center, 0)
    for (let ring = 1; ring <= ringCount; ring += 1) {
      const fraction = ring / ringCount
      for (let sample = 0; sample < perimeter; sample += 1) {
        const side = Math.floor(sample / edgeSamples)
        const edgePoint = corners[side]!.clone()
          .lerp(corners[(side + 1) % corners.length]!, (sample % edgeSamples) / edgeSamples)
          .normalize()
        appendVertex(center.clone().lerp(edgePoint, fraction).normalize(), fraction)
      }
    }
    for (let sample = 0; sample < perimeter; sample += 1) {
      indices.push(base, base + 1 + sample, base + 1 + (sample + 1) % perimeter)
    }
    for (let ring = 1; ring < ringCount; ring += 1) {
      const inner = base + 1 + (ring - 1) * perimeter
      const outer = inner + perimeter
      for (let sample = 0; sample < perimeter; sample += 1) {
        const next = (sample + 1) % perimeter
        indices.push(inner + sample, outer + sample, outer + next)
        indices.push(inner + sample, outer + next, inner + next)
      }
    }
  })

  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  geometry.setIndex(indices)
  geometry.computeVertexNormals()
  return geometry
}

export function createLeatherGrain() {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 256
  const context = canvas.getContext('2d')!
  context.fillStyle = '#888888'
  context.fillRect(0, 0, 256, 256)
  let seed = 7127
  const random = () => {
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  }
  for (let index = 0; index < 5000; index += 1) {
    const x = random() * 256
    const y = random() * 256
    const shade = Math.round(90 + random() * 90)
    context.fillStyle = `rgb(${shade}, ${shade}, ${shade})`
    context.beginPath()
    context.ellipse(x, y, 0.6 + random() * 1.1, 0.5 + random() * 0.7, random() * Math.PI, 0, Math.PI * 2)
    context.fill()
  }
  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping
  texture.anisotropy = 8
  return texture
}
