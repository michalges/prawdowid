import { ImageManipulator, SaveFormat } from 'expo-image-manipulator'

import { ERRORS } from '@/constants/labels'

const MAX_IMAGE_B64_CHARS = Math.floor((5 * 1024 * 1024 * 4) / 3)
const MAX_IMAGE_WIDTH = 1600
const COMPRESS_STEPS = [0.8, 0.6, 0.4]

/** Resizes and compresses on-device to fit the API's 5 MB image limit (CONCEPT §7.6). */
export async function getImageBase64(uri: string): Promise<string> {
  let rendered
  try {
    rendered = await ImageManipulator.manipulate(uri, { maxWidth: MAX_IMAGE_WIDTH }).renderAsync()
  } catch {
    throw new Error(ERRORS.imageUnreadable)
  }
  for (const compress of COMPRESS_STEPS) {
    // oxlint-disable-next-line no-await-in-loop -- each step only runs if the previous one was too large
    const { base64 } = await rendered.saveAsync({ format: SaveFormat.JPEG, compress, base64: true })
    if (base64 && base64.length <= MAX_IMAGE_B64_CHARS) return base64
  }
  throw new Error(ERRORS.imageTooLarge)
}
