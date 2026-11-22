const { AndroidConfig, withAndroidManifest } = require('expo/config-plugins')

const DEFAULT_CATEGORY = { $: { 'android:name': 'android.intent.category.DEFAULT' } }

function getIntentFilter(action, mimeType, label) {
  return {
    $: label ? { 'android:label': label } : {},
    action: [{ $: { 'android:name': action } }],
    category: [DEFAULT_CATEGORY],
    data: [{ $: { 'android:mimeType': mimeType } }],
  }
}

function isSameFilter(left, right) {
  return (
    JSON.stringify(left.action) === JSON.stringify(right.action) &&
    JSON.stringify(left.data) === JSON.stringify(right.data)
  )
}

/**
 * Registers the main activity for the system Share menu (text + images) and the text-selection
 * menu (ACTION_PROCESS_TEXT). See CONCEPT §7.6.
 */
module.exports = function withAndroidShareIntents(config, { processTextLabel, allowCleartextTraffic = false } = {}) {
  return withAndroidManifest(config, (modConfig) => {
    const manifest = modConfig.modResults
    const mainActivity = AndroidConfig.Manifest.getMainActivityOrThrow(manifest)
    const filters = [
      getIntentFilter('android.intent.action.SEND', 'text/plain'),
      getIntentFilter('android.intent.action.SEND', 'image/*'),
      getIntentFilter('android.intent.action.PROCESS_TEXT', 'text/plain', processTextLabel),
    ]
    const existing = mainActivity['intent-filter'] ?? []
    mainActivity['intent-filter'] = [
      ...existing.filter((filter) => !filters.some((added) => isSameFilter(filter, added))),
      ...filters,
    ]
    if (allowCleartextTraffic) {
      AndroidConfig.Manifest.getMainApplicationOrThrow(manifest).$['android:usesCleartextTraffic'] = 'true'
    }
    return modConfig
  })
}
