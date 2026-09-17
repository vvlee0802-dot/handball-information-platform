import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  calculateChunkCount,
  createVideoFingerprint,
  deleteVideo,
  formatBytes,
  formatDuration,
  retryVideoProcessing,
  validateVideoFile,
  type VideoUploadPolicy,
} from '@/services/videos'


const policy: VideoUploadPolicy = {
  accepted_extensions: ['.mp4'],
  accepted_content_types: ['application/mp4', 'video/mp4'],
  max_size_bytes: 32,
  chunk_size_bytes: 8,
}

describe('video upload validation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })
  it('accepts an MP4 within the configured size limit', () => {
    const file = new File(['valid-video'], 'full-match.mp4', { type: 'video/mp4' })

    expect(validateVideoFile(file, policy)).toBeNull()
  })

  it('rejects unsupported extensions and media types', () => {
    const mov = new File(['video'], 'full-match.mov', { type: 'video/quicktime' })
    const wrongType = new File(['video'], 'full-match.mp4', { type: 'video/quicktime' })

    expect(validateVideoFile(mov, policy)).toBe('仅支持 MP4 格式的视频。')
    expect(validateVideoFile(wrongType, policy)).toBe('文件的媒体类型不是 MP4。')
  })

  it('rejects oversized files and formats binary sizes for the interface', () => {
    const file = new File(['x'.repeat(33)], 'full-match.mp4', { type: 'video/mp4' })

    expect(validateVideoFile(file, policy)).toContain('上传上限')
    expect(formatBytes(10 * 1024 ** 3)).toBe('10.0 GiB')
  })

  it('submits a failed processing task for retry', async () => {
    const responseBody = { id: 7, processing_status: 'queued' }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(retryVideoProcessing(7)).resolves.toEqual(responseBody)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/videos/7/retry',
      expect.objectContaining({ method: 'POST', credentials: 'include' }),
    )
  })

  it('builds a stable file fingerprint and upload plan for resuming', () => {
    const file = new File(['0123456789abcdef'], 'match.mp4', {
      type: 'video/mp4',
      lastModified: 123456,
    })

    expect(createVideoFingerprint(file)).toBe('match.mp4:16:123456')
    expect(calculateChunkCount(file.size, policy.chunk_size_bytes)).toBe(2)
  })

  it('formats video duration for the management list', () => {
    expect(formatDuration(65)).toBe('1:05')
    expect(formatDuration(3723.5)).toBe('1:02:04')
    expect(formatDuration(null)).toBe('待识别')
  })

  it('deletes a video through the protected API', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(deleteVideo(9)).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/videos/9',
      expect.objectContaining({ method: 'DELETE', credentials: 'include' }),
    )
  })
})
