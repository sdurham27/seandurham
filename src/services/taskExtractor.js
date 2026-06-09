import Anthropic from '@anthropic-ai/sdk'

const SYSTEM = `You are an intelligent assistant that monitors conversation transcripts and extracts actionable items for the user.

Your job is to identify:
- Tasks the user needs to do or agreed to do
- Follow-ups the user should make (call someone back, reply to someone, check on something)
- Reminders the user mentioned or that were mentioned to the user
- Notes about something the user should pay closer attention to

Rules:
- Only extract items clearly relevant to the user (assigned to them, requested of them, or something they committed to)
- Ignore items assigned to other people
- Be concise — task text should be actionable and brief
- If nothing new and actionable was said, return an empty array
- Do not duplicate tasks already in the existing list`

export async function extractTasks(transcriptChunks, existingTasks, userName, apiKey) {
  const client = new Anthropic({ apiKey, dangerouslyAllowBrowser: true })

  const recentTranscript = transcriptChunks.slice(-4).join('\n---\n')
  const existingList = existingTasks.length
    ? existingTasks.map(t => `- ${t.text}`).join('\n')
    : '(none yet)'

  const userLabel = userName ? `The user's name is ${userName}.` : ''

  const prompt = `${userLabel}

Recent conversation transcript (last few minutes):
"""
${recentTranscript}
"""

Already captured tasks (do not duplicate these):
${existingList}

Extract any NEW actionable items from the transcript. Return ONLY a JSON array with no markdown, no explanation. Each item:
{
  "text": "brief actionable description",
  "type": "task" | "follow_up" | "reminder" | "note",
  "context": "one sentence of why this is relevant",
  "priority": "high" | "medium" | "low"
}

If nothing new to extract, return: []`

  const msg = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 1024,
    system: SYSTEM,
    messages: [{ role: 'user', content: prompt }],
  })

  const raw = msg.content[0]?.text?.trim() || '[]'

  // Strip markdown code fences if present
  const cleaned = raw.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/i, '').trim()

  try {
    const parsed = JSON.parse(cleaned)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter(item => item.text && item.type)
      .map(item => ({
        id: crypto.randomUUID(),
        text: item.text,
        type: item.type,
        context: item.context || '',
        priority: item.priority || 'medium',
        done: false,
        createdAt: Date.now(),
      }))
  } catch {
    return []
  }
}
