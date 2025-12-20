/**
 * Utility functions for generating EVE Online image URLs
 * Uses the official EVE Online image server for character portraits and corp/alliance logos
 */

// EVE Online image server base URL
const EVE_IMAGE_SERVER = 'https://images.evetech.net'

/**
 * Generate URL for character portrait
 * @param characterId - EVE Online character ID
 * @param size - Image size (32, 64, 128, 256, 512, 1024)
 * @returns URL string for character portrait
 */
export const getCharacterPortraitUrl = (characterId: number, size: number = 128): string => {
  return `${EVE_IMAGE_SERVER}/characters/${characterId}/portrait?size=${size}`
}

/**
 * Generate URL for corporation logo
 * @param corporationId - EVE Online corporation ID
 * @param size - Image size (32, 64, 128, 256)
 * @returns URL string for corporation logo
 */
export const getCorporationLogoUrl = (corporationId: number, size: number = 128): string => {
  return `${EVE_IMAGE_SERVER}/corporations/${corporationId}/logo?size=${size}`
}

/**
 * Generate URL for alliance logo
 * @param allianceId - EVE Online alliance ID
 * @param size - Image size (32, 64, 128, 256)
 * @returns URL string for alliance logo
 */
export const getAllianceLogoUrl = (allianceId: number, size: number = 128): string => {
  return `${EVE_IMAGE_SERVER}/alliances/${allianceId}/logo?size=${size}`
}

/**
 * Preload an image to improve loading performance
 * @param url - Image URL to preload
 * @returns Promise that resolves when image is loaded
 */
export const preloadImage = (url: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve()
    img.onerror = () => reject(new Error(`Failed to load image: ${url}`))
    img.src = url
  })
}

/**
 * Generate fallback image URL (placeholder)
 * @param type - Type of entity ('character', 'corporation', 'alliance')
 * @returns Data URL for a simple SVG placeholder
 */
export const getFallbackImageUrl = (type: 'character' | 'corporation' | 'alliance'): string => {
  const colors = {
    character: '#3b82f6', // blue
    corporation: '#8b5cf6', // purple
    alliance: '#eab308' // yellow
  }
  
  const icons = {
    character: '👤',
    corporation: '🏢',
    alliance: '👑'
  }
  
  const color = colors[type]
  const icon = icons[type]
  
  // Create a simple SVG placeholder
  const svg = `
    <svg width="128" height="128" xmlns="http://www.w3.org/2000/svg">
      <rect width="128" height="128" fill="${color}" opacity="0.2"/>
      <text x="64" y="74" text-anchor="middle" font-size="48" fill="${color}">${icon}</text>
    </svg>
  `
  
  return `data:image/svg+xml;base64,${btoa(svg)}`
}
