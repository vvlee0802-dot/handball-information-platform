import { describe, expect, it } from 'vitest'

import { formatBytes, validateVideoFile, type VideoUploadPolicy } from '@/services/videos'


const policy: VideoUploadPolicy = {
  accepted_extensions: ['.mp4'],
  accepted_content_types: ['application/mp4', 'video/mp4'],
  max_size_bytes: 32,
}

describe('video upload validation', () => {
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
})
