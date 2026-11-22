import { NativeModule, requireOptionalNativeModule } from 'expo'

export type SharePayload =
  | { kind: 'text'; text: string; subject: string | null; source: 'share' | 'process_text' }
  | { kind: 'image'; uri: string; source: 'share' }

type ShareIntentEvents = { onShare(payload: SharePayload): void }

declare class ShareIntentModule extends NativeModule<ShareIntentEvents> {
  getInitialShare(): Promise<SharePayload | null>
}

/** Android only; null elsewhere (web, iOS) so the app still runs without share entry points. */
export default requireOptionalNativeModule<ShareIntentModule>('ShareIntent')
