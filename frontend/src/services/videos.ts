import { ApiError, apiRequest } from '@/services/http'

export interface VideoRecord {
  id: number
  match_id: number
  uploaded_by_user_id: number
  original_filename: string
  content_type: string
  size_bytes: number
  status: 'uploaded'
  created_at: string
}

export interface VideoUploadPolicy {
  accepted_extensions: string[]
  accepted_content_types: string[]
  max_size_bytes: number
}

export const getVideoUploadPolicy = () =>
  apiRequest<VideoUploadPolicy>('/api/videos/upload-policy')

export const listMatchVideos = (matchId: number) =>
  apiRequest<VideoRecord[]>(`/api/matches/${matchId}/videos`)

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

export const uploadMatchVideo = (
  matchId: number,
  file: File,
  onProgress: (percent: number) => void,
) =>
  new Promise<VideoRecord>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', `/api/matches/${matchId}/videos`)
    xhr.withCredentials = true
    xhr.setRequestHeader('Accept', 'application/json')
    xhr.setRequestHeader('Content-Type', file.type || 'video/mp4')
    xhr.setRequestHeader('X-Original-Filename', encodeURIComponent(file.name))
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as VideoRecord)
        return
      }
      reject(new ApiError(readUploadError(xhr), xhr.status))
    })
    xhr.addEventListener('error', () => reject(new Error('网络连接中断，视频上传失败。')))
    xhr.send(file)
  })
