const readErrorMessage = async (response: Response) => {
  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>
    }

    if (typeof body.detail === 'string') return body.detail

    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((issue) => issue.msg)
        .filter((message): message is string => Boolean(message))

      if (messages.length > 0) return messages.join('；')
    }

    return `请求失败（${response.status}）`
  } catch {
    return `请求失败（${response.status}）`
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type ApiRequestOptions = RequestInit & {
  redirectOnUnauthorized?: boolean
}

export const apiRequest = async <T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> => {
  const { redirectOnUnauthorized = true, ...fetchOptions } = options
  const response = await fetch(path, {
    ...fetchOptions,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
  })

  if (!response.ok) {
    const message = await readErrorMessage(response)
    if (response.status === 401 && redirectOnUnauthorized && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) return undefined as T

  return response.json() as Promise<T>
}
