// === CONFIG ===
const ALLOWED_TOKENS = [
  'nmtURUHthfmil5HmIM18dQiBrceFFWcg6nXryqUZjqc',      // share ONLY with jawad@multiply.ae
  'mW6x8fR9Q2sG0KZJ4vFj1t8qPZpVnYh3cL7dE5sA2Bk'       // share ONLY with a.tamer@mmg.global
];
const TOKEN_TO_USER = {
  'nmtURUHthfmil5HmIM18dQiBrceFFWcg6nXryqUZjqc': 'jawad@multiply.ae',
  'mW6x8fR9Q2sG0KZJ4vFj1t8qPZpVnYh3cL7dE5sA2Bk': 'a.tamer@mmg.global'
};
const SHEET_ID = '1fUlPoJCEXWT4uSumoV4W1PzP2DHRVcdGV5P4OdoNKyE';
const SHEET_NAME = 'Articles';
const GMAIL_URL = 'https://mail.google.com/mail/u/0/#inbox';

// === SAVE ===
function saveToSheet_(p) {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  // if (sh.getLastRow() === 0) sh.appendRow(['Timestamp','Section','Title','URL','Summary','User']);
  const user = TOKEN_TO_USER[p.token] || '';
  sh.appendRow([new Date(), p.section, p.title, p.url, p.summary, user]);
}

// === UI ===
function renderHtml_(title, message, isError) {
  const color = isError ? '#ff6b6b' : '#4CAF50';
  const html = `
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${title}</title>
    <style>
      body { background:#0a0a0a; color:#fff; font-family:Arial,sans-serif; margin:0; padding:24px; }
      .card { background:#1a1a1a; border:1px solid #333; border-radius:8px; padding:24px; max-width:720px; margin:48px auto; }
      .title { color:${color}; font-size:22px; margin:0 0 8px 0; }
      .msg { color:#ccc; margin:0 0 20px 0; line-height:1.5; }
      .btns { display:flex; gap:10px; }
      .btn { background:#4fc3f7; color:#000; border:none; border-radius:6px; padding:10px 14px; font-weight:bold; cursor:pointer; }
      .btn.secondary { background:#333; color:#fff; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1 class="title">${title}</h1>
      <p class="msg">${message}</p>
      <div class="btns">
        <button id="close" class="btn">Cancel</button>
        <button id="gmail" class="btn secondary">Back to Gmail</button>
      </div>
    </div>
    <script>
      document.getElementById('close').addEventListener('click', function () {
        try { window.open('', '_self'); window.close(); setTimeout(function(){ window.location.href = '${GMAIL_URL}'; }, 300); }
        catch (e) { window.location.href = '${GMAIL_URL}'; }
      });
      document.getElementById('gmail').addEventListener('click', function () {
        window.location.href = '${GMAIL_URL}';
      });
    </script>
  </body>
</html>`;
  return HtmlService.createHtmlOutput(html).setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// === ENTRY ===
function doGet(e) {
  const token = (e.parameter.auth || '').trim();
  if (!ALLOWED_TOKENS.includes(token)) {
    return renderHtml_('Not authorized', 'This web app is restricted. Invalid or missing token.', true);
  }
  const payload = {
    title: e.parameter.title || '',
    url: e.parameter.url || '',
    section: e.parameter.section || '',
    summary: e.parameter.summary || '',
    token
  };
  try {
    saveToSheet_(payload);
    return renderHtml_('Saved ✅', 'The article was saved successfully. You can close this tab or return to Gmail.', false);
  } catch (err) {
    return renderHtml_('Save failed ❌', 'There was an error saving the article. Please try again.', true);
  }
}