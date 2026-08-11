/** 人设字段规范化与摘要（官方只读人设） */

export const PERSONA_CONTENT_KEYS = [
  'name',
  'age',
  'avatar_url',
  'region',
  'metaphor',
  'identity',
  'tone',
  'catchphrases',
  'interests',
  'intimacy_stages',
  'relationship_boundary',
  'taboos',
  'personality',
  'openings',
  'easter_eggs',
]

/** @param {unknown} value */
function asList(value) {
  if (Array.isArray(value)) return value
  if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) return parsed
    } catch {
      return value
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
    }
  }
  return []
}

/** @param {Record<string, any> | null | undefined} detail */
export function normalizePersona(detail) {
  const d = detail || {}
  return {
    name: (d.name || '').trim(),
    age: Number(d.age) > 0 ? Number(d.age) : 0,
    avatar_url: (d.avatar_url || '').trim(),
    region: (d.region || '').trim(),
    metaphor: (d.metaphor || '').trim(),
    identity: (d.identity || '').trim(),
    tone: (d.tone || '').trim(),
    catchphrases: asList(d.catchphrases),
    interests: (d.interests || '').trim(),
    intimacy_stages: asList(d.intimacy_stages),
    relationship_boundary: (d.relationship_boundary || '').trim(),
    taboos: (d.taboos || '').trim(),
    personality: (d.personality || '').trim(),
    openings: asList(d.openings),
    easter_eggs: asList(d.easter_eggs),
  }
}

/**
 * 将人设 avatar_url 转为前端可请求地址（走 /api 代理）
 * @param {string} url
 */
export function resolvePersonaAvatar(url) {
  const raw = (url || '').trim()
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw) || raw.startsWith('data:')) return raw
  const prefix = (import.meta.env.VITE_API_PREFIX || '/api').replace(/\/$/, '')
  if (raw.startsWith('/')) return `${prefix}${raw}`
  return `${prefix}/${raw}`
}

/** @param {Record<string, any>} a @param {Record<string, any>} b */
export function personasEqual(a, b) {
  return JSON.stringify(normalizePersona(a)) === JSON.stringify(normalizePersona(b))
}

/** @param {Record<string, any>} persona */
export function buildPersonaSummary(persona) {
  const p = normalizePersona(persona)
  const lines = []
  if (p.region) lines.push(`地区：${p.region}`)
  if (p.identity) lines.push(`身份：${p.identity}`)
  if (p.tone) lines.push(`语气：${p.tone}`)
  if (p.interests) lines.push(`兴趣：${p.interests.replace(/\n/g, ' / ')}`)
  if (p.relationship_boundary) lines.push(`边界：${p.relationship_boundary}`)
  if (p.taboos) lines.push(`禁忌：${p.taboos}`)
  return lines.join('\n')
}
