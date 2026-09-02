import type { ChatDone, DocRecord } from '../types'

async function toJson<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = await resp.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // 非 JSON 错误体,沿用 statusText
    }
    throw new Error(`请求失败(${resp.status}):${detail}`)
  }
  return resp.json() as Promise<T>
}

export async function listDocs(): Promise<DocRecord[]> {
  return toJson<DocRecord[]>(await fetch('/api/documents/list'))
}

export interface UploadResult {
  doc_id: string
  status: string
}

export async function uploadDoc(file: File): Promise<UploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  return toJson<UploadResult>(await fetch('/api/documents/upload', { method: 'POST', body: fd }))
}

export async function deleteDoc(docId: string): Promise<void> {
  await toJson(await fetch(`/api/documents/${docId}`, { method: 'DELETE' }))
}

/**
 * SSE 流式问答:后端经 POST /api/chat/stream 推送 "data: {...}" 事件,末尾 "event: end\ndata: [DONE]"。
 * onDelta 收到打字机片段;onDone 收到最终结果(所有 delta 拼接 == done.answer)。
 */
export async function askStream(
  query: string,
  onDelta: (text: string) => void,
  onDone: (done: ChatDone) => void,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
    signal,
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`流式请求失败(${resp.status})`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    // SSE 事件以空行分隔
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      for (const line of block.split('\n')) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6)
        if (payload === '[DONE]') return
        const ev = JSON.parse(payload) as { type: string; text?: string } & ChatDone
        if (ev.type === 'delta' && ev.text) onDelta(ev.text)
        else if (ev.type === 'done') onDone(ev)
      }
    }
    if (done) break
  }
}
