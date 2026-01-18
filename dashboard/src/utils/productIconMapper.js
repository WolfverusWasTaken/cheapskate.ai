const PRODUCT_ICONS = {
  // Phones
  iphone: '📱',
  samsung: '📱',
  pixel: '📱',
  phone: '📱',

  // Audio
  airpods: '🎧',
  headphones: '🎧',
  earbuds: '🎧',
  speaker: '🔊',

  // Computers
  macbook: '💻',
  laptop: '💻',
  imac: '🖥️',
  mac: '🖥️',

  // Tablets
  ipad: '📱',
  tablet: '📱',

  // Watches
  watch: '⌚',

  // Gaming
  playstation: '🎮',
  xbox: '🎮',
  nintendo: '🎮',
  switch: '🎮',

  // Cameras
  camera: '📷',
  gopro: '📷',

  // Default
  default: '📦'
}

/**
 * Get emoji icon for a product name
 * @param {string} productName
 * @returns {string} Emoji
 */
export function getProductIcon(productName) {
  const lowerName = productName.toLowerCase()

  for (const [keyword, icon] of Object.entries(PRODUCT_ICONS)) {
    if (keyword !== 'default' && lowerName.includes(keyword)) {
      return icon
    }
  }

  return PRODUCT_ICONS.default
}
