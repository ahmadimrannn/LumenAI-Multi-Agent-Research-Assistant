import type { LumenEvent } from "@/lib/types"

export async function* readEvents(response: Response): AsyncGenerator<LumenEvent> {
  if (!response.body) throw new Error("The response has no body")
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let index: number
    while ((index = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, index)
      buffer = buffer.slice(index + 2)
      for (const line of block.split("\n")) {
        if (!line.startsWith("data:")) continue
        const payload = line.slice(5).trim()
        if (payload === "[DONE]") return
        if (payload) yield JSON.parse(payload) as LumenEvent
      }
    }
  }
}
