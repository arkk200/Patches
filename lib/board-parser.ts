export interface GameBoard {
  size: number
  grid: (number | null)[][]
  colors: Record<number, string>
}

const COLOR_MAP: Record<string, string> = {
  blu: '#3B82F6', // Blue 500
  pur: '#8B5CF6', // Purple 500
  ora: '#F97316', // Orange 500
  red: '#EF4444', // Red 500
  bro: '#B45309', // Amber 700 (Brownish)
  gre: '#10B981', // Emerald 500
  yel: '#F59E0B', // Amber 500
  pin: '#EC4899', // Pink 500
}

/**
 * Parses a custom ASCII grid and color mapping text into a GameBoard object.
 * @param text The raw text content from a daily record file.
 * @returns A GameBoard object.
 */
export function parseBoard(text: string): GameBoard {
  const lines = text.trim().split('\n')
  const gridLines: string[] = []
  const colorLines: string[] = []
  let isColorSection = false

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (trimmed.startsWith('# colors')) {
      isColorSection = true
      continue
    }

    if (isColorSection) {
      colorLines.push(trimmed)
    } else {
      gridLines.push(trimmed)
    }
  }

  // Parse Grid
  const grid: (number | null)[][] = gridLines.map((line) => {
    // Handle both space-separated and no-space formats
    // If the line contains spaces, split by spaces/tabs
    // If not, split char by char
    // if some numbers are over 9, split by spaces/tabs
    const tokens = line.includes(' ') ? line.split(/\s+/) : line.split('')

    return tokens.map((token) => {
      if (token === '.' || token === '0' || token === '_') return null
      const num = parseInt(token, 10)
      return isNaN(num) ? null : num
    })
  })

  // Ensure grid is N x N
  const size = grid.length

  // Parse Colors
  const colors: Record<number, string> = {}
  for (const line of colorLines) {
    const [numStr, colorStr] = line.split(':').map((s) => s.trim())
    const num = parseInt(numStr, 10)
    if (!isNaN(num)) {
      colors[num] = COLOR_MAP[colorStr.toLowerCase()] || colorStr
    }
  }

  return { size, grid, colors }
}
