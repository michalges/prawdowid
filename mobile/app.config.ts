import type { ExpoConfig } from 'expo/config'

const DEFAULT_API_URL = 'http://10.0.2.2:5173'
const apiUrl = process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_API_URL

const config: ExpoConfig = {
  name: 'Prawdowid',
  slug: 'prawdowid',
  version: '0.1.0',
  orientation: 'portrait',
  icon: './assets/images/icon.png',
  scheme: 'prawdowid',
  userInterfaceStyle: 'light',
  android: {
    package: 'pl.prawdowid.app',
    adaptiveIcon: {
      backgroundColor: '#d4213d',
      foregroundImage: './assets/images/android-icon-foreground.png',
      monochromeImage: './assets/images/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
  },
  web: {
    output: 'static',
    favicon: './assets/images/favicon.png',
  },
  plugins: [
    'expo-router',
    ['expo-splash-screen', { backgroundColor: '#ffffff', image: './assets/images/splash-icon.png', imageWidth: 96 }],
    'expo-secure-store',
    ['expo-image-picker', { photosPermission: 'Prawdowid odczytuje wybrany zrzut ekranu, żeby sprawdzić jego treść.' }],
    [
      './plugins/withAndroidShareIntents.js',
      { processTextLabel: 'Sprawdź w Prawdowidzie', allowCleartextTraffic: apiUrl.startsWith('http://') },
    ],
  ],
  extra: { apiUrl },
  experiments: {
    typedRoutes: true,
    reactCompiler: true,
  },
}

export default config
