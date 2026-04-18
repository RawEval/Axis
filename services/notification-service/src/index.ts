import Fastify from 'fastify';
import { dispatchPush, type PushPayload } from './push/dispatch.js';

const app = Fastify({ logger: true });

// Postgres for device token lookups
const DATABASE_URL = process.env.DATABASE_URL ?? 'postgresql://axis:axis@localhost:5433/axis';

// Lazy pg import — only connect when a push route is actually hit
let pgPool: any = null;
async function getPool() {
  if (pgPool) return pgPool;
  const { default: pg } = await import('pg');
  pgPool = new pg.Pool({ connectionString: DATABASE_URL });
  return pgPool;
}

app.get('/healthz', async () => ({ status: 'ok', service: 'notification-service' }));

// ---------- Push ----------

app.post<{ Body: { userId: string; title: string; body: string; data?: Record<string, string> } }>(
  '/push',
  async (req) => {
    const { userId, title, body, data } = req.body;
    const pool = await getPool();
    const { rows } = await pool.query(
      'SELECT platform, token FROM user_devices WHERE user_id = $1::uuid',
      [userId],
    );
    if (rows.length === 0) {
      return { ok: true, message: 'no devices registered', tokensTargeted: 0 };
    }
    return dispatchPush({ userId, title, body, data }, rows);
  },
);

// ---------- Device registration ----------

app.post<{ Body: { userId: string; platform: string; token: string } }>(
  '/devices/register',
  async (req) => {
    const { userId, platform, token } = req.body;
    if (!['ios', 'android', 'web'].includes(platform)) {
      return { ok: false, error: 'platform must be ios, android, or web' };
    }
    const pool = await getPool();
    await pool.query(
      `INSERT INTO user_devices (user_id, platform, token)
       VALUES ($1::uuid, $2, $3)
       ON CONFLICT (platform, token) DO UPDATE SET user_id = $1::uuid, last_seen_at = NOW()`,
      [userId, platform, token],
    );
    return { ok: true, platform, registered: true };
  },
);

app.post<{ Body: { token: string } }>('/devices/revoke', async (req) => {
  const pool = await getPool();
  const { rows } = await pool.query(
    'DELETE FROM user_devices WHERE token = $1 RETURNING id',
    [req.body.token],
  );
  return { ok: true, deleted: rows.length };
});

// ---------- Email ----------

app.post<{ Body: { to: string; subject: string; html: string } }>('/email', async (req) => {
  // Phase 2: send via Resend. Currently logs for Mailhog or no-ops.
  app.log.info({ to: req.body.to, subject: req.body.subject }, 'email stub');
  return { ok: true, to: req.body.to, stub: true };
});

// ---------- Start ----------

const port = Number(process.env.PORT ?? 8005);
app.listen({ port, host: '0.0.0.0' }).catch((err) => {
  app.log.error(err);
  process.exit(1);
});
