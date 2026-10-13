export function cleanLatexMath(text) {
  if (!text) return ''
  const greek = {
    alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε',
    zeta: 'ζ', eta: 'η', theta: 'θ', iota: 'ι', kappa: 'κ',
    lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', pi: 'π',
    rho: 'ρ', sigma: 'σ', tau: 'τ', upsilon: 'υ', phi: 'φ',
    chi: 'χ', psi: 'ψ', omega: 'ω',
  }
  let cleaned = text
  for (const [name, sym] of Object.entries(greek)) {
    cleaned = cleaned.replace(new RegExp(`\\$\\\\?${name}\\$`, 'gi'), sym)
    cleaned = cleaned.replace(new RegExp(`\\\\${name}\\b`, 'gi'), sym)
  }
  cleaned = cleaned.replace(/\$([A-Za-z0-9_\-+^/]+)\$/g, '$1')
  return cleaned
}

export function parseAnswerBlocks(text) {
  if (!text) return []
  const rawLines = text.split('\n').filter((l) => l.trim().length > 0)
  const blocks = []
  let currentCard = null

  for (const rawLine of rawLines) {
    const trimmed = rawLine.trim()

    // H3: Main Topic
    if (trimmed.startsWith('### ')) {
      currentCard = null
      blocks.push({ type: 'h3', content: trimmed.replace(/^###\s+/, '') })
      continue
    }

    // H4: Subheading
    if (trimmed.startsWith('#### ')) {
      currentCard = null
      blocks.push({ type: 'h4', content: trimmed.replace(/^####\s+/, '') })
      continue
    }

    // Horizontal rule
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      currentCard = null
      blocks.push({ type: 'divider' })
      continue
    }

    // Disclaimer or educational note
    if (
      trimmed.includes('summarizes the retrieved educational material') ||
      trimmed.includes('individual diagnosis') ||
      trimmed.includes('simulated plain-model baseline') ||
      trimmed.startsWith('*Disclaimer:') ||
      trimmed.startsWith('Disclaimer:')
    ) {
      currentCard = null
      blocks.push({ type: 'disclaimer', content: trimmed })
      continue
    }

    // Indented sub-bullet (2+ leading spaces or tab before bullet, or sub-bullet symbol)
    const isSubBullet = /^(\s{2,}|\t+)[•\-\*]\s+/.test(rawLine) || /^[◦▪▫]\s+/.test(trimmed)
    // Main/parent bullet (0-1 leading spaces)
    const isParentBullet = /^\s{0,1}[•\-\*]\s+/.test(rawLine)

    if (isSubBullet && currentCard) {
      const content = trimmed.replace(/^([•\-\*◦▪▫]|\d+\.)\s+/, '')
      currentCard.children.push(content)
      continue
    }

    if (isParentBullet) {
      let content = trimmed.replace(/^[•\-\*]\s+/, '')
      // Remove any (Layer 1), (Layer 2), (Layer 3) labels
      content = content.replace(/\s*\(Layer\s*\d+\)/gi, '')

      // Check if this bullet card contains numbered items like 1) ... 2) ... or 1. ... 2. ...
      const hasNumberedSequence = /(?:^|[\s:])1[\)\.]\s+[\s\S]*?(?:[\s;])2[\)\.]\s+/i.test(content)
      if (hasNumberedSequence) {
        const matchFirstNum = content.match(/^(.*?)(?:[:\s]|^)(1[\)\.]\s+[\s\S]*)$/)
        if (matchFirstNum) {
          const rawLead = matchFirstNum[1].trim()
          const leadIntro = rawLead ? (rawLead.endsWith(':') ? rawLead : `${rawLead}:`) : ''
          const numberedBody = matchFirstNum[2]

          const segments = numberedBody
            .split(/(?=(?:^|\s)[1-9][0-9]*[\)\.]\s+)/)
            .map((s) => s.trim())
            .filter(Boolean)

          currentCard = {
            type: 'bullet_card',
            parent: leadIntro || segments[0],
            children: leadIntro ? segments : segments.slice(1),
          }
          blocks.push(currentCard)
          continue
        }
      }

      currentCard = {
        type: 'bullet_card',
        parent: content,
        children: [],
      }
      blocks.push(currentCard)
      continue
    }

    // Unbulleted indented continuation line
    if (currentCard && /^\s{2,}/.test(rawLine)) {
      currentCard.children.push(trimmed.replace(/\s*\(Layer\s*\d+\)/gi, ''))
      continue
    }

    // Regular paragraph
    currentCard = null
    blocks.push({ type: 'paragraph', content: trimmed.replace(/\s*\(Layer\s*\d+\)/gi, '') })
  }

  return blocks
}
