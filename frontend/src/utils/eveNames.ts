/**
 * Utility functions for fetching real entity names from EVE Online ESI API
 */

// EVE Online ESI API base URL
const ESI_BASE_URL = 'https://esi.evetech.net/latest'

// Cache for storing resolved names to avoid repeated API calls
const nameCache = new Map<string, string>()

/**
 * Extract ID from placeholder name (e.g., "Character_91658177" -> 91658177)
 */
const extractIdFromPlaceholder = (placeholderName: string): number | null => {
  const match = placeholderName.match(/_(\d+)$/)
  return match ? parseInt(match[1], 10) : null
}

/**
 * Check if a name is a placeholder (contains underscore followed by numbers)
 */
const isPlaceholderName = (name: string): boolean => {
  return /^(Character|Corporation|Alliance)_\d+$/.test(name)
}

/**
 * Fetch character names from EVE ESI API
 */
export const fetchCharacterNames = async (characterIds: number[]): Promise<Map<number, string>> => {
  const nameMap = new Map<number, string>()
  
  if (characterIds.length === 0) return nameMap

  try {
    const response = await fetch(`${ESI_BASE_URL}/universe/names/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(characterIds),
    })

    if (response.ok) {
      const names = await response.json()
      names.forEach((item: { id: number; name: string }) => {
        nameMap.set(item.id, item.name)
        nameCache.set(`character_${item.id}`, item.name)
      })
    }
  } catch (error) {
    console.warn('Failed to fetch character names from ESI:', error)
  }

  return nameMap
}

/**
 * Fetch corporation names from EVE ESI API
 */
export const fetchCorporationNames = async (corporationIds: number[]): Promise<Map<number, string>> => {
  const nameMap = new Map<number, string>()
  
  if (corporationIds.length === 0) return nameMap

  try {
    const response = await fetch(`${ESI_BASE_URL}/universe/names/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(corporationIds),
    })

    if (response.ok) {
      const names = await response.json()
      names.forEach((item: { id: number; name: string }) => {
        nameMap.set(item.id, item.name)
        nameCache.set(`corporation_${item.id}`, item.name)
      })
    }
  } catch (error) {
    console.warn('Failed to fetch corporation names from ESI:', error)
  }

  return nameMap
}

/**
 * Fetch alliance names from EVE ESI API
 */
export const fetchAllianceNames = async (allianceIds: number[]): Promise<Map<number, string>> => {
  const nameMap = new Map<number, string>()
  
  if (allianceIds.length === 0) return nameMap

  try {
    const response = await fetch(`${ESI_BASE_URL}/universe/names/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(allianceIds),
    })

    if (response.ok) {
      const names = await response.json()
      names.forEach((item: { id: number; name: string }) => {
        nameMap.set(item.id, item.name)
        nameCache.set(`alliance_${item.id}`, item.name)
      })
    }
  } catch (error) {
    console.warn('Failed to fetch alliance names from ESI:', error)
  }

  return nameMap
}

/**
 * Resolve a character name - if it's a placeholder, fetch the real name
 */
export const resolveCharacterName = async (name: string, characterId: number): Promise<string> => {
  // If name is not a placeholder, return as-is
  if (!isPlaceholderName(name)) {
    return name
  }

  // Check cache first
  const cacheKey = `character_${characterId}`
  if (nameCache.has(cacheKey)) {
    return nameCache.get(cacheKey)!
  }

  // Fetch from ESI
  const nameMap = await fetchCharacterNames([characterId])
  return nameMap.get(characterId) || name
}

/**
 * Resolve a corporation name - if it's a placeholder, fetch the real name
 */
export const resolveCorporationName = async (name: string, corporationId: number): Promise<string> => {
  // If name is not a placeholder, return as-is
  if (!isPlaceholderName(name)) {
    return name
  }

  // Check cache first
  const cacheKey = `corporation_${corporationId}`
  if (nameCache.has(cacheKey)) {
    return nameCache.get(cacheKey)!
  }

  // Fetch from ESI
  const nameMap = await fetchCorporationNames([corporationId])
  return nameMap.get(corporationId) || name
}

/**
 * Resolve an alliance name - if it's a placeholder, fetch the real name
 */
export const resolveAllianceName = async (name: string, allianceId: number): Promise<string> => {
  // If name is not a placeholder, return as-is
  if (!isPlaceholderName(name)) {
    return name
  }

  // Check cache first
  const cacheKey = `alliance_${allianceId}`
  if (nameCache.has(cacheKey)) {
    return nameCache.get(cacheKey)!
  }

  // Fetch from ESI
  const nameMap = await fetchAllianceNames([allianceId])
  return nameMap.get(allianceId) || name
}

/**
 * Batch resolve all entity names for better performance
 */
export const batchResolveNames = async (data: {
  players: Array<{ character_id: number; character_name: string }>
  corporations: Array<{ corporation_id: number; corporation_name: string }>
  alliances: Array<{ alliance_id: number; alliance_name: string }>
}) => {
  // Collect all IDs that need resolution
  const characterIds = data.players
    .filter(p => isPlaceholderName(p.character_name))
    .map(p => p.character_id)

  const corporationIds = data.corporations
    .filter(c => isPlaceholderName(c.corporation_name))
    .map(c => c.corporation_id)

  const allianceIds = data.alliances
    .filter(a => isPlaceholderName(a.alliance_name))
    .map(a => a.alliance_id)

  // Fetch all names in parallel
  const [characterNames, corporationNames, allianceNames] = await Promise.all([
    fetchCharacterNames(characterIds),
    fetchCorporationNames(corporationIds),
    fetchAllianceNames(allianceIds)
  ])

  return {
    characterNames,
    corporationNames,
    allianceNames
  }
}
