// 外发队列真发：读 Supabase mail_messages 中 status=pending_send，经 mail.pony-it.com:587 发送，回写状态，并自动复制到 IMAP Sent 资料夹。
const nodemailer = require('nodemailer');
const tls = require('tls');
const SB = {
  url: 'https://xlcyumbyqcwedqwpspzs.supabase.co',
  key: 'sb_publishable_FlQqq0Zg6PgO_bJ9FuLGWw_MdgpYpe5'
};
const SMTP = { host: 'mail.pony-it.com', port: 587, secure: false, pass: process.env.MAIL_PWD || '123456' };
const IMAP = { host: 'mail.pony-it.com', port: 993 };

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

// 构建 RFC822 原始邮件
function buildRawMail(row) {
  const now = new Date();
  const dateStr = now.toUTCString();
  const body = row.body || '';
  return [
    'From: ' + row.from_identity,
    'To: ' + row.to_addr,
    'Subject: ' + (row.subject || '(no subject)'),
    'Date: ' + dateStr,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=utf-8',
    '',
    body
  ].join('\r\n');
}

// IMAP APPEND 把邮件存入 Sent
function appendToSent(user, pass, rawMail) {
  return new Promise((resolve, reject) => {
    let buf = '';
    let step = 0;
    const socket = tls.connect(IMAP.port, IMAP.host, { rejectUnauthorized: false }, () => {
      socket.write('a1 LOGIN ' + user + ' ' + pass + '\r\n');
    });
    socket.setTimeout(20000);
    socket.on('timeout', () => { socket.destroy(new Error('IMAP timeout')); });
    socket.on('data', (d) => {
      buf += d.toString();
      while (buf.includes('\r\n')) {
        const lineEnd = buf.indexOf('\r\n');
        const line = buf.slice(0, lineEnd);
        buf = buf.slice(lineEnd + 2);
        if (step === 0 && line.includes('OK')) {
          // login ok, find Sent folder
          socket.write('a2 LIST "" "*"\r\n');
          step = 1;
        } else if (step === 1 && line.startsWith('a2')) {
          // list done
          socket.write('a3 SELECT "Sent"\r\n');
          step = 2;
        } else if (step === 2 && line.startsWith('a3')) {
          // sent selected, now append
          const len = Buffer.byteLength(rawMail, 'utf8');
          socket.write('a4 APPEND "Sent" {' + len + '}\r\n');
          step = 3;
        } else if (step === 3 && line.includes('+')) {
          // ready for literal
          socket.write(rawMail + '\r\na5 LOGOUT\r\n');
          step = 4;
        } else if (step === 4 && line.startsWith('a5')) {
          socket.end();
          resolve();
        }
      }
    });
    socket.on('error', (e) => reject(e));
  });
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
      // 自动存入 IMAP Sent
      try {
        const raw = buildRawMail(row);
        await appendToSent(row.from_identity, SMTP.pass, raw);
        console.log('[send_pending] appended to Sent: ' + row.from_identity);
      } catch (imapErr) {
        console.log('[send_pending] Sent append warning: ' + imapErr.message);
      }
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
