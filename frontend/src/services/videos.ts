import { ApiError, apiRequest } from '@/services/http'

export type VideoProcessingStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface VideoRecord {
  id: number
  match_id: number
  uploaded_by_user_id: number
  original_filename: string
  content_type: string
  size_bytes: number
  status: 'uploaded'
  processing_status: VideoProcessingStatus
  processing_progress: number
  processing_attempts: number
  failure_reason: string | null
  checksum_sha256: string | null
  processing_started_at: string | null
  processing_completed_at: string | null
  created_at: string
}

export interface VideoUploadPolicy {
  accepted_extensions: string[]
  accepted_content_types: string[]
  max_size_bytes: number
  chunk_size_bytes: number
}

export interface VideoUploadPart {
  part_number: number
  size_bytes: number
  checksum_sha256: string
}

export interface VideoUploadSession {
  id: string
  match_id: number
  original_filename: string
  total_size: number
  chunk_size: number
  total_parts: number
  status: 'uploading' | 'assembling' | 'completed' | 'cancelled' | 'failed'
  uploaded_parts: VideoUploadPart[]
  video_id: number | null
  created_at: string
  updated_at: string
}

export interface ResumableUploadOptions {
  signal?: AbortSignal
  onProgress: (percent: number) => void
  onResume?: (uploadedParts: number, percent: number) => void
}

export const getVideoUploadPolicy = () =>
  apiRequest<VideoUploadPolicy>('/api/videos/upload-policy')

export const listMatchVideos = (matchId: number) =>
  apiRequest<VideoRecord[]>(`/api/matches/${matchId}/videos`)

export const retryVideoProcessing = (videoId: number) =>
  apiRequest<VideoRecord>(`/api/videos/${videoId}/retry`, { method: 'POST' })

export const validateVideoFile = (file: File, policy: VideoUploadPolicy): string | null => {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!policy.accepted_extensions.includes(extension)) return '仅支持 MP4 格式的视频。'
  if (file.type && !policy.accepted_content_types.includes(file.type)) {
    return '文件的媒体类型不是 MP4。'
  }
  if (file.size === 0) return '不能上传空文件。'
  if (file.size > policy.max_size_bytes) {
    return `文件超过 ${formatBytes(policy.max_size_bytes)} 的上传上限。`
  }
  return null
}

export const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KiB', 'MiB', 'GiB', 'TiB']
  let value = bytes / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[unitIndex]}`
}

const readUploadError = (xhr: XMLHttpRequest) => {
  try {
    const response = JSON.parse(xhr.responseText) as { detail?: string }
    return response.detail || `上传失败（${xhr.status}）`
  } catch {
    return `上传失败（${xhr.status}）`
  }
}

export const createVideoFingerprint = (file: File) =>
  `${file.name}:${file.size}:${file.lastModified}`

export const calculateChunkCount = (fileSize: number, chunkSize: number) =>
  Math.ceil(fileSize / chunkSize)

const calculateSha256 = async (chunk: Blob) => {
  const digest = await crypto.subtle.digest('SHA-256', await chunk.arrayBuffer())
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

const uploadPartOnce = (
  sessionId: string,
  partNumber: number,
  chunk: Blob,
  checksum: string,
  signal: AbortSignal | undefined,
  onProgress: (loaded: number) => void,
) =>
  new Promise<VideoUploadPart>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', `/api/video-uploads/${sessionId}/parts/${partNumber}`)
    xhr.withCredentials = true
    xhr.setRequestHeader('Accept', 'application/json')
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.setRequestHeader('X-Chunk-SHA256', checksum)
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) onProgress(event.loaded)
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as VideoUploadPart)
        return
      }
      reject(new ApiError(readUploadError(xhr), xhr.status))
    })
    xhr.addEventListener('error', () => reject(new Error('网络连接中断，当前分片上传失败。')))
    xhr.addEventListener('abort', () => reject(new DOMException('上传已取消', 'AbortError')))
    const abort = () => xhr.abort()
    signal?.addEventListener('abort', abort, { once: true })
    xhr.addEventListener('loadend', () => signal?.removeEventListener('abort', abort))
    xhr.send(chunk)
  })

const uploadPartWithRetry = async (
  sessionId: string,
  partNumber: number,
  chunk: Blob,
  checksum: string,
  signal: AbortSignal | undefined,
  onProgress: (loaded: number) => void,
) => {
  let lastError: unknown
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      return await uploadPartOnce(
        sessionId,
        partNumber,
        chunk,
        checksum,
        signal,
        onProgress,
      )
    } catch (error) {
      lastError = error
      if (signal?.aborted || (error instanceof ApiError && error.status < 500)) throw error
    }
  }
  throw lastError
}

export const cancelVideoUpload = (sessionId: string) =>
  apiRequest<VideoUploadSession>(`/api/video-uploads/${sessionId}`, { method: 'DELETE' })

export const uploadMatchVideoResumable = async (
  matchId: number,
  file: File,
  options: ResumableUploadOptions,
): Promise<VideoRecord> => {
  let session: VideoUploadSession | null = null
  try {
    session = await apiRequest<VideoUploadSession>(`/api/matches/${matchId}/video-uploads`, {
      method: 'POST',
      signal: options.signal,
      body: JSON.stringify({
        original_filename: file.name,
        content_type: file.type || 'video/mp4',
        total_size: file.size,
        fingerprint: createVideoFingerprint(file),
      }),
    })

    const uploadedPartNumbers = new Set(session.uploaded_parts.map((part) => part.part_number))
    let completedBytes = session.uploaded_parts.reduce((total, part) => total + part.size_bytes, 0)
    const resumedPercent = Math.round((completedBytes / file.size) * 100)
    if (uploadedPartNumbers.size > 0) {
      options.onResume?.(uploadedPartNumbers.size, resumedPercent)
      options.onProgress(resumedPercent)
    }

    for (let partNumber = 1; partNumber <= session.total_parts; partNumber += 1) {
      if (uploadedPartNumbers.has(partNumber)) continue
      if (options.signal?.aborted) throw new DOMException('上传已取消', 'AbortError')
      const start = (partNumber - 1) * session.chunk_size
      const end = Math.min(start + session.chunk_size, file.size)
      const chunk = file.slice(start, end)
      const checksum = await calculateSha256(chunk)
      await uploadPartWithRetry(
        session.id,
        partNumber,
        chunk,
        checksum,
        options.signal,
        (loaded) => options.onProgress(Math.round(((completedBytes + loaded) / file.size) * 100)),
      )
      completedBytes += chunk.size
      options.onProgress(Math.round((completedBytes / file.size) * 100))
    }

    return await apiRequest<VideoRecord>(`/api/video-uploads/${session.id}/complete`, {
      method: 'POST',
      signal: options.signal,
    })
  } catch (error) {
    if (options.signal?.aborted && session !== null) {
      await cancelVideoUpload(session.id).catch(() => undefined)
    }
    throw error
  }
}
