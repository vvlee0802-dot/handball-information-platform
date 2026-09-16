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

export const apiRequest = async <T>(path: string, options: RequestInit = {}): Promise<T> => {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) throw new Error(await readErrorMessage(response))

  return response.json() as Promise<T>
}
