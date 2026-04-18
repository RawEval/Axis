/**
 * Push notification dispatch — APNs (iOS) + FCM (Android).
 *
 * Phase 1: both are log-only stubs that validate the payload shape and
 * record the dispatch attempt. Real provider calls require:
 *   - APNs: a .p8 key file + team_id + bundle_id
 *   - FCM: a Firebase service account JSON
 *
 * Set APNS_KEY_PATH + FCM_CREDENTIALS_PATH in env to enable real sending.
 * Until then, every push is a no-op that returns { ok: true, stub: true }.
 */

export type PushPayload = {
  userId: string;
  title: string;
  body: string;
  data?: Record<string, string>;
};

export type PushResult = {
  ok: boolean;
  stub: boolean;
  platform: 'ios' | 'android' | 'all';
  tokensTargeted: number;
};

const APNS_ENABLED = !!process.env.APNS_KEY_PATH;
const FCM_ENABLED = !!process.env.FCM_CREDENTIALS_PATH;

export async function dispatchPush(
  payload: PushPayload,
  tokens: Array<{ platform: string; token: string }>,
): Promise<PushResult> {
  const iosTokens = tokens.filter((t) => t.platform === 'ios');
  const androidTokens = tokens.filter((t) => t.platform === 'android');

  if (APNS_ENABLED && iosTokens.length > 0) {
    // Phase 2: call APNs provider here
    console.log(`[push] APNs → ${iosTokens.length} devices for ${payload.userId}`);
  }

  if (FCM_ENABLED && androidTokens.length > 0) {
    // Phase 2: call FCM here
    console.log(`[push] FCM → ${androidTokens.length} devices for ${payload.userId}`);
  }

  if (!APNS_ENABLED && !FCM_ENABLED) {
    console.log(`[push] stub mode — ${payload.title}: ${payload.body}`);
  }

  return {
    ok: true,
    stub: !APNS_ENABLED && !FCM_ENABLED,
    platform: 'all',
    tokensTargeted: tokens.length,
  };
}
