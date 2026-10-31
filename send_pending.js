// 外发队列真发：读 Supabase mail_messages 中 status=pending_send，经 mail.pony-it.com:587 STARTTLS 发送，回写状态。
// 由定时巡查任务在每轮邮件同步后调用：node send_pending.js
const nodemailer = require('nodemailer');
const SB = {
  url: 'https://xlcyumbyqcwedqwpspzs.supabase.co',
  key: 'sb_publishable_FlQqq0Zg6PgO_bJ9FuLGWw_MdgpYpe5'
};
const SMTP = { host: 'mail.pony-it.com', port: 587, secure: false, pass: process.env.MAIL_PWD || '123456' };

async function api(path, opts = {}) {
  const r = await fetch(SB.url + '/rest/v1/' + path, {
    ...opts,
    headers: {
      apikey: SB.key,
      Authorization: 'Bearer ' + SB.key,
      'Content-Type': 'application/json',
      Prefer: opts.prefer || '',
      ...(opts.headers || {})
    }
  });
  const txt = await r.text();
  let data = null; try { data = JSON.parse(txt); } catch (e) {}
  return { status: r.status, data };
}

async function main() {
  const pend = await api("mail_messages?select=*&status=eq.pending_send&order=id.asc&limit=20");
  const rows = pend.data || [];
  console.log('[send_pending] pending =', rows.length);
  for (const row of rows) {
    try {
      const tx = nodemailer.createTransport({
        host: SMTP.host, port: SMTP.port, secure: SMTP.secure,
        auth: { user: row.from_identity, pass: SMTP.pass }
      });
      const info = await tx.sendMail({
        from: row.from_identity,
        to: row.to_addr,
        subject: row.subject || '(no subject)',
        text: row.body || ''
      });
      await api('mail_messages?id=eq.' + row.id, {
        method: 'PATCH', prefer: 'return=minimal',
        body: JSON.stringify({ status: 'sent', sent_at: new Date().toISOString(), note: 'SMTP ok ' + (info.messageId || '') })
      });
      console.log('[send_pending] sent id=' + row.id + ' -> ' + row.to_addr + ' msg=' + info.messageId);
    } catch (e) {
      await api('mail_messages?id=eq.' + row.id, {
        method: 'PATCH', prefer: 'return=minimal',
        body: JSON.stringify({ status: 'failed', note: String(e.message || e).slice(0, 300) })
      });
      console.log('[send_pending] FAIL id=' + row.id + ' ' + e.message);
    }
  }
}
main().catch(e => { console.error(e); process.exit(1); });
