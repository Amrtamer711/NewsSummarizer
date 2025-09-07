from datetime import datetime, timedelta
import os
import shutil
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from storage import init_db, save_digest, get_digest, save_article, list_saved_articles, is_article_saved, delete_article_by_url, list_digest_dates_between
from send_email import fetch_ai_news, fetch_news, MODEL_CONFIG, LLM_ENABLED, STOCKS, plot_stock_chart, SECTION_ORDER
from stock_metrics import get_comprehensive_stock_metrics, format_metrics_html, generate_stock_summary_table
from config import PERPLEXITY_API_KEY, STATIC_DIR
from clients import client as openai_client, gemini_client
from notifier import send_outlook_email
from config import BASE_PUBLIC_URL

app = Flask(__name__)
init_db()

# Configure Flask to serve static files from data directory
app.static_folder = STATIC_DIR
app.static_url_path = '/static'

BASE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>NewsAI</title>
  <style>
    :root{--bg:#0a0a0a;--panel:#141414;--card:#1a1a1a;--border:#2a2a2a;--accent:#4fc3f7;--good:#4CAF50;--warn:#ffa726;--text:#fff;--muted:#aaa}
    *{box-sizing:border-box}
    body{background:var(--bg);color:var(--text);font-family:Inter,Arial,sans-serif;margin:0}
    header{position:sticky;top:0;background:var(--panel);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;gap:16px;z-index:10}
    a.nav{color:var(--accent);text-decoration:none;font-weight:600;padding:6px 10px;border-radius:8px}
    a.nav.active{background:var(--accent);color:#000}
    .container{max-width:1200px;margin:0 auto;padding:20px}
    .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 1px 10px rgba(0,0,0,.25);overflow:hidden}
    .btn{background:var(--good);color:#fff;border:none;border-radius:8px;padding:8px 12px;cursor:pointer}
    .btn.danger{background:#ff6b6b;padding:7px 10px}
    a.btn{ text-decoration:none }
    a.btn:hover{ text-decoration:none }
    .meta{color:var(--muted);font-size:12px}
    h1{margin:0 0 14px 0}
    h2{margin:20px 0 10px 0}
    /* Calendar */
    .cal-wrap{display:grid;grid-template-columns:repeat(7,1fr);gap:10px}
    .cal-day{background:var(--card);border:1px solid var(--border);border-radius:10px;min-height:90px;padding:10px;position:relative}
    .cal-day .d{position:absolute;top:8px;right:10px;color:var(--muted);font-size:12px;z-index:2}
    .cal-day.has{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
    .cal-day .full-link{position:absolute;inset:0;border-radius:10px;cursor:pointer}
    .cal-head{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin-bottom:8px;color:var(--muted)}
    .cal-nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
    .link{background:transparent;border:1px solid var(--border);color:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;text-decoration:none}
  </style>
</head>
<body>
  <header>
    <a class="nav {% if nav_active == 'today' %}active{% endif %}" href="/">Today</a>
    <a class="nav {% if nav_active == 'calendar' %}active{% endif %}" href="/calendar">Calendar</a>
    <a class="nav {% if nav_active == 'saved' %}active{% endif %}" href="/saved">Saved</a>
    <a class="nav {% if nav_active == 'stocks' %}active{% endif %}" href="/stocks">Weekly Stocks</a>
  </header>
  <div class="container">{{ content|safe }}</div>
  <script>
  // Global save/unsave toggle (works on all pages)
  function slideOutAndRemove(el){
    const h = el.scrollHeight;
    el.style.maxHeight = h + 'px';
    el.style.transition = 'max-height .25s ease, opacity .25s ease, transform .25s ease, margin .25s ease, padding .25s ease';
    requestAnimationFrame(()=>{
      el.style.opacity = '0';
      el.style.transform = 'translateX(-12px)';
      el.style.maxHeight = '0';
      el.style.marginTop = '0';
      el.style.marginBottom = '0';
      el.style.paddingTop = '0';
      el.style.paddingBottom = '0';
    });
    setTimeout(()=>{ el.remove(); }, 280);
  }
  document.addEventListener('click', async (e)=>{
    const btn = e.target.closest('.save-toggle');
    if (!btn) return;
    e.preventDefault();
    const payload = new URLSearchParams();
    payload.append('title', btn.dataset.title || '');
    payload.append('url', btn.dataset.url || '');
    payload.append('summary', btn.dataset.summary || '');
    payload.append('section', btn.dataset.section || '');
    try {
      const res = await fetch('/api/toggle', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: payload});
      const data = await res.json();
      if (data.ok){
        btn.textContent = data.saved ? 'Unsave' : 'Save';
        if (!data.saved && window.location.pathname === '/saved'){
          const card = btn.closest('.card');
          if (card) slideOutAndRemove(card);
        }
      }
    } catch (err) { console.error(err); }
  });
  </script>
</body>
</html>
"""

ARTICLE_ITEM = """
<div class="card">
  <a href="{{ url }}" style="color:#4fc3f7;font-weight:bold;text-decoration:none;font-size:16px">{{ title }}</a>
  {% if summary %}<p style="color:#ccc">{{ summary }}</p>{% endif %}
  <div class="meta">{{ section }}</div>
  <div style="margin-top:8px">
    <button class="btn save-toggle" data-title="{{ title|e }}" data-url="{{ url|e }}" data-summary="{{ summary|e }}" data-section="{{ section|e }}">{{ saved_label }}</button>
  </div>
</div>
"""


def _ensure_static_dir():
    # Use the configured static directory from config
    os.makedirs(STATIC_DIR, exist_ok=True)
    return STATIC_DIR


def _cleanup_old_charts(keep_days=7):
    """Remove stock chart PNG files older than keep_days."""
    try:
        import glob
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        pattern = os.path.join(STATIC_DIR, "*_7d.png")
        
        for filepath in glob.glob(pattern):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_mtime < cutoff_time:
                os.remove(filepath)
                print(f"🧹 Cleaned up old chart: {os.path.basename(filepath)}")
    except Exception as e:
        print(f"⚠️ Chart cleanup error: {e}")


def _build_weekly_stocks_html(date: datetime) -> str:
    # Build full stock section (summary + detailed), move charts to /static, replace cid: refs
    static_dir = _ensure_static_dir()
    
    # Clean up old charts before generating new ones
    _cleanup_old_charts(keep_days=30)  # Keep charts for 30 days
    
    stock_metrics_list = []
    stock_imgs = []
    # Prepare LLM clients and config identical to email job
    llm_clients = {
        'openai': openai_client if LLM_ENABLED.get('openai') else None,
        'gemini': gemini_client if LLM_ENABLED.get('gemini') else None,
    }
    llm_cfg = dict(MODEL_CONFIG)
    llm_cfg['perplexity_api_key'] = PERPLEXITY_API_KEY
    print("\n📈 Monday Stocks: building weekly stocks HTML...", flush=True)
    for s in STOCKS:
        try:
            print(f"\n📊 Fetching metrics for {s['name']} ({s['ticker']})...", flush=True)
            m = get_comprehensive_stock_metrics(
                s['ticker'], s['name'], llm_enabled=LLM_ENABLED, llm_config=llm_cfg, clients=llm_clients, logger=None
            )
        except Exception:
            continue
        stock_metrics_list.append(m)
        # Print key numbers like email
        if m and 'error' not in m:
            try:
                print(f"  ✓ Current Price: {m['section_a']['Current Price']}", flush=True)
                print(f"  ✓ Week Change: {m['section_a']['% Change WoW']}", flush=True)
                print(f"  ✓ Market Cap: {m['section_a']['Market Cap']}", flush=True)
                print(f"  ✓ P/E Ratio: {m['section_a']['P/E Ratio']}", flush=True)
                print(f"  ✓ Revenue: {m['section_b']['TTM Revenue']}", flush=True)
                print(f"  ✓ EBITDA Margin: {m['section_b']['EBITDA Margin']}", flush=True)
                if m.get('news'):
                    print(f"  ✓ Latest News: {m['news'][0]['title'][:60]}...", flush=True)
                if m.get('categorized_news'):
                    print("  ✓ Categorized updates ready", flush=True)
                if m.get('section_c'):
                    print("  ✓ Operational updates ready", flush=True)
                if m.get('analyst_signal'):
                    print(f"  ✓ Analyst Signal: {m['analyst_signal']}", flush=True)
            except Exception:
                pass
        # chart
        try:
            print(f"  📈 Generating 7-day chart...", flush=True)
            path = plot_stock_chart(s['ticker'], s['name'])
            # move/copy to static
            filename = os.path.basename(path)
            target = os.path.join(static_dir, filename)
            try:
                shutil.copyfile(path, target)
            except Exception:
                pass
            stock_imgs.append({'name': s['name'], 'ticker': s['ticker'], 'img_path': target})
            print(f"  ✓ Chart saved to: {target}", flush=True)
        except Exception:
            pass
    if not stock_metrics_list:
        return ''
    # Build HTML using existing helpers
    summary_html = generate_stock_summary_table(stock_metrics_list)
    detailed_html = format_metrics_html(stock_metrics_list, stock_imgs)
    html = summary_html + detailed_html
    # Replace cid: refs with /static/actual
    for s in STOCKS:
        cid = s['ticker'].replace('.', '').replace('-', '')
        filename = f"{s['ticker']}_7d.png"
        html = html.replace(f"cid:{cid}", f"/static/{filename}")
    return html


def _find_latest_stocks_date() -> str | None:
    today = datetime.now()
    # search back up to 180 days
    start = (today - timedelta(days=180)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    dates = sorted(list(list_digest_dates_between(start, end)))
    dates.sort(reverse=True)
    for ds in dates:
        d = get_digest(ds)
        if d and d.get('stocks_html'):
            return ds
    return None


def build_digest_for_date(date: datetime):
    # NOTE: used by offline job/cron only; not called from HTTP routes
    ai = fetch_ai_news()
    direct = fetch_news()
    merged = {}
    for sec in set(ai.keys()).union(direct.keys()):
        merged[sec] = ai.get(sec, []) + direct.get(sec, [])
    
    # Refine articles to best 6 per section before saving
    from news_fetchers import refine_articles, is_recent_article, check_articles_for_hallucinations
    refined_sections = {}
    for section, articles in merged.items():
        # Filter by date first
        recent_articles = [a for a in articles if is_recent_article(a)]
        
        # Check for hallucinations BEFORE refining
        print(f"\n\n{'='*60}")
        print(f"Processing section: {section}")
        print(f"{'='*60}")
        
        # Only check AI-sourced articles for hallucinations
        ai_articles = [a for a in recent_articles if a.get('client') in ['OpenAI', 'Perplexity', 'Gemini']]
        non_ai_articles = [a for a in recent_articles if a.get('client') not in ['OpenAI', 'Perplexity', 'Gemini']]
        
        if ai_articles:
            verified_ai_articles = check_articles_for_hallucinations(ai_articles, section, days_back=3)
            verified_articles = verified_ai_articles + non_ai_articles
        else:
            verified_articles = recent_articles
        
        # Then refine to best 6
        if LLM_ENABLED.get('openai') and verified_articles:
            refined = refine_articles(
                articles=verified_articles,
                section=section,
                openai_client=openai_client,
                model=MODEL_CONFIG["openai_model"],
                max_articles=6
            )
            refined_sections[section] = refined
        else:
            # If OpenAI disabled, just take first 6
            refined_sections[section] = verified_articles[:6]
    
    # No need for additional URL fixing since we already verified and fixed URLs in hallucination checker
    final_sections = refined_sections
    
    payload = {
        'date': date.strftime('%Y-%m-%d'),
        'sections': final_sections,
    }
    # Weekly stocks on Mondays
    if date.weekday() == 0:
        try:
            payload['stocks_html'] = _build_weekly_stocks_html(date)
        except Exception:
            payload['stocks_html'] = ''
    save_digest(payload['date'], payload)
    # Send Outlook notification email with links
    try:
        ds = payload['date']
        today_link = f"{BASE_PUBLIC_URL}/"
        calendar_link = f"{BASE_PUBLIC_URL}/calendar?date={ds}"
        stocks_link = f"{BASE_PUBLIC_URL}/stocks" if payload.get('stocks_html') else None
        is_monday = date.weekday() == 0
        subject = ("📊 Weekly Stocks + News digest ready" if is_monday else "📰 Daily news digest ready")
        body = "<div style='font-family:Arial,sans-serif'>"
        body += f"<p>Digest for <b>{ds}</b> is ready.</p>"
        body += f"<p><a href='{today_link}'>Open Today</a> · <a href='{calendar_link}'>Open Calendar ({ds})</a>"
        if stocks_link:
            body += f" · <a href='{stocks_link}'>Open Weekly Stocks</a>"
        body += "</p>"
        body += "<p style='color:#666;font-size:12px'>This is an automated notification.</p>"
        body += "</div>"
        to_list = [os.environ.get('OUTLOOK_NOTIFY_TO') or os.environ.get('OUTLOOK_SMTP_USER','')]
        to_list = [x for x in to_list if x]
        if to_list:
            send_outlook_email(subject, body, to_list)
    except Exception:
        pass
    return payload


@app.route('/')
def today():
    date_str = datetime.now().strftime('%Y-%m-%d')
    digest = get_digest(date_str)
    if not digest:
        msg = f"""
        <div class=card>
          <h2 style='color:#ffa726;margin:0 0 8px 0'>No digest available for {date_str}</h2>
          <p style='color:#ccc;margin:0'>The background job hasn’t generated today’s digest yet. It usually takes ~45 minutes. Try again later.</p>
        </div>
        """
        return render_template_string(BASE_HTML, content=msg, nav_active='today')
    parts = []
    # Weekly Stocks (if present)
    if digest.get('stocks_html'):
        parts.append("<div class='card'><h2 style='margin:0 0 10px 0'>Weekly Stocks</h2>" + digest['stocks_html'] + "</div>")
    # News sections
    items_html = ''
    # Enforce desired section order
    rendered_sections = set()
    for section in SECTION_ORDER:
        items = digest['sections'].get(section)
        if not items:
            continue
        rendered_sections.add(section)
        items_html += f"<h2 style=\"color:#4fc3f7\">{section}</h2>"
        for it in items[:6]:
            saved = is_article_saved(it.get('url','#'))
            label = 'Unsave' if saved else 'Save'
            search_url = f"https://www.google.com/search?q={quote(it.get('title',''))}"
            items_html += render_template_string(ARTICLE_ITEM, title=it.get('title','Untitled'), url=it.get('url','#'), summary=it.get('summary',''), section=section, saved_label=label, search_url=search_url)
    # Render any remaining sections (if present)
    for section, items in digest['sections'].items():
        if section in rendered_sections:
            continue
        items_html += f"<h2 style=\"color:#4fc3f7\">{section}</h2>"
        for it in items[:6]:
            saved = is_article_saved(it.get('url','#'))
            label = 'Unsave' if saved else 'Save'
            search_url = f"https://www.google.com/search?q={quote(it.get('title',''))}"
            items_html += render_template_string(ARTICLE_ITEM, title=it.get('title','Untitled'), url=it.get('url','#'), summary=it.get('summary',''), section=section, saved_label=label, search_url=search_url)
    parts.append(items_html)
    content = f"<h1>Today's Digest – {date_str}</h1>" + ''.join(parts)
    return render_template_string(BASE_HTML, content=content, nav_active='today')


@app.route('/calendar')
def calendar_view():
    # Month params
    today = datetime.now()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    first = datetime(year, month, 1)
    # calc grid start (Monday=0)
    start = first - timedelta(days=(first.weekday()))
    end = start + timedelta(days=41)  # 6 weeks view
    # fetch available digest dates set
    have = list_digest_dates_between(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

    # header/nav
    prev_m = (first - timedelta(days=1)).replace(day=1)
    next_m = (first + timedelta(days=32)).replace(day=1)
    head = f"""
    <div class=cal-nav>
      <a class=link href=\"/calendar?year={prev_m.year}&month={prev_m.month}\">← {prev_m.strftime('%b %Y')}</a>
      <h1 style=\"margin:0\">{first.strftime('%B %Y')}</h1>
      <a class=link href=\"/calendar?year={next_m.year}&month={next_m.month}\">{next_m.strftime('%b %Y')} →</a>
    </div>
    <div class=cal-head>
      <div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div><div>Sun</div>
    </div>
    """
    # days grid
    days_html = '<div class="cal-wrap">'
    cur = start
    for _ in range(42):
        ds = cur.strftime('%Y-%m-%d')
        has = ds in have
        klass = 'cal-day has' if has else 'cal-day'
        link = f"<a class='full-link' href='/calendar?year={year}&month={month}&date={ds}' aria-label='Open digest for {ds}'></a>" if has else ''
        days_html += f"<div class='{klass}'><div class='d'>{cur.day}</div>{link}</div>"
        cur += timedelta(days=1)
    days_html += '</div>'

    # if a date is clicked, render digest below
    q = request.args.get('date')
    bottom = ''
    if q:
        digest = get_digest(q)
        if digest:
            parts = [f"<h2>Digest – {q}</h2>"]
            if digest.get('stocks_html'):
                parts.append("<div class='card'><h3 style='margin:0 0 8px 0'>Weekly Stocks</h3>" + digest['stocks_html'] + "</div>")
            items_html = ''
            rendered_sections = set()
            for section in SECTION_ORDER:
                items = digest['sections'].get(section)
                if not items:
                    continue
                rendered_sections.add(section)
                items_html += f"<h3 style=\"color:#4fc3f7\">{section}</h3>"
                for it in items[:6]:
                    saved = is_article_saved(it.get('url','#'))
                    label = 'Unsave' if saved else 'Save'
                    search_url = f"https://www.google.com/search?q={quote(it.get('title',''))}"
                    items_html += render_template_string(ARTICLE_ITEM, title=it.get('title','Untitled'), url=it.get('url','#'), summary=it.get('summary',''), section=section, saved_label=label, search_url=search_url)
            for section, items in digest['sections'].items():
                if section in rendered_sections:
                    continue
                items_html += f"<h3 style=\"color:#4fc3f7\">{section}</h3>"
                for it in items[:6]:
                    saved = is_article_saved(it.get('url','#'))
                    label = 'Unsave' if saved else 'Save'
                    search_url = f"https://www.google.com/search?q={quote(it.get('title',''))}"
                    items_html += render_template_string(ARTICLE_ITEM, title=it.get('title','Untitled'), url=it.get('url','#'), summary=it.get('summary',''), section=section, saved_label=label, search_url=search_url)
            parts.append(items_html)
            bottom = ''.join(parts)
        else:
            bottom = f"<div class=card><p style='color:var(--muted)'>No digest for {q}</p></div>"

    return render_template_string(BASE_HTML, content=head + days_html + bottom, nav_active='calendar')


@app.route('/saved')
def saved():
    rows = list_saved_articles()
    # Group by published_date (UAE), fallback to saved_at
    def pick_date(r):
        dsrc = r.get('published_date') or r.get('saved_at')
        try:
            dt = datetime.fromisoformat(dsrc.replace('Z','').split('T')[0] + 'T00:00:00')
            return dt.date().isoformat()
        except Exception:
            return (r.get('published_date') or r.get('saved_at'))[:10]
    html = '<h1>Saved Articles</h1>'
    last_date = None
    for r in rows:
        d = pick_date(r)
        if d != last_date:
            html += f'<h2 style="color:#4fc3f7">{d}</h2>'
            last_date = d
        search_url = f"https://www.google.com/search?q={quote(r.get('title',''))}"
        html += render_template_string(ARTICLE_ITEM, title=r['title'], url=r['url'], summary=r.get('summary',''), section=r.get('section',''), saved_label='Unsave', search_url=search_url)
    return render_template_string(BASE_HTML, content=html, nav_active='saved')


@app.route('/api/save', methods=['POST'])
def api_save():
    title = request.form.get('title','').strip()
    url = request.form.get('url','').strip()
    summary = request.form.get('summary','').strip()
    section = request.form.get('section','').strip()
    published_date = request.form.get('published_date','').strip()
    if not title or not url:
        return jsonify({'ok': False, 'error': 'missing title/url'}), 400
    save_article(title, url, section, summary, published_date)
    return redirect(request.referrer or url_for('saved'))


@app.route('/api/toggle', methods=['POST'])
def api_toggle():
    title = request.form.get('title','').strip()
    url = request.form.get('url','').strip()
    summary = request.form.get('summary','').strip()
    section = request.form.get('section','').strip()
    published_date = request.form.get('published_date','').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'missing url'}), 400
    if is_article_saved(url):
        delete_article_by_url(url)
        return jsonify({'ok': True, 'saved': False})
    else:
        save_article(title or url, url, section, summary, published_date)
        return jsonify({'ok': True, 'saved': True})


@app.route('/health')
def health():
    return 'OK', 200


@app.route('/stocks')
def stocks():
    # Optional ?date=YYYY-MM-DD, otherwise show most recent available stocks digest
    q = request.args.get('date')
    ds = q
    if not ds:
        ds = _find_latest_stocks_date()
    if not ds:
        msg = """
        <div class=card>
          <h2 style='margin:0 0 8px 0'>Weekly Stocks</h2>
          <p class=meta>No weekly stocks digest found yet. It is generated by the Monday cron run.</p>
        </div>
        """
        return render_template_string(BASE_HTML, content=msg, nav_active='stocks')
    dig = get_digest(ds)
    if not dig or not dig.get('stocks_html'):
        msg = f"""
        <div class=card>
          <h2 style='margin:0 0 8px 0'>Weekly Stocks</h2>
          <p class=meta>No stocks content for {ds}.</p>
        </div>
        """
        return render_template_string(BASE_HTML, content=msg, nav_active='stocks')
    content = f"<h1>Weekly Stocks — {ds}</h1><div class='card'>" + dig['stocks_html'] + "</div>"
    return render_template_string(BASE_HTML, content=content, nav_active='stocks')


@app.route('/api/trigger/daily-digest', methods=['POST'])
def trigger_daily_digest():
    """Single endpoint for daily digest - handles both news and Monday stocks"""
    # Get auth token from header or query param
    auth_token = request.headers.get('X-Auth-Token') or request.args.get('auth_token')
    expected_token = os.environ.get('CRON_AUTH_TOKEN')
    
    if not expected_token or auth_token != expected_token:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        date = datetime.now()
        is_monday = date.weekday() == 0
        
        digest_type = "daily news + weekly stocks" if is_monday else "daily news"
        print(f"🔄 Triggered {digest_type} collection for {date.strftime('%Y-%m-%d')}")
        
        # Run the digest build (includes stocks automatically on Mondays)
        payload = build_digest_for_date(date)
        
        return jsonify({
            'success': True,
            'date': payload['date'],
            'digest_type': digest_type,
            'is_monday': is_monday,
            'sections': {k: len(v) for k, v in payload['sections'].items()},
            'has_stocks': bool(payload.get('stocks_html'))
        }), 200
    except Exception as e:
        print(f"❌ Error in daily digest trigger: {e}")
        return jsonify({'error': str(e)}), 500


# Keep the old endpoints for backward compatibility but have them redirect
@app.route('/api/trigger/daily-news', methods=['POST'])
def trigger_daily_news():
    """Legacy endpoint - redirects to daily-digest"""
    return trigger_daily_digest()


@app.route('/api/trigger/weekly-stocks', methods=['POST'])
def trigger_weekly_stocks():
    """Legacy endpoint - redirects to daily-digest"""
    return trigger_daily_digest()


@app.route('/api/cleanup-charts', methods=['POST'])
def cleanup_charts():
    """Manually trigger cleanup of old chart files."""
    auth_token = request.headers.get('X-Auth-Token') or request.args.get('auth_token')
    expected_token = os.environ.get('CRON_AUTH_TOKEN')
    
    if not expected_token or auth_token != expected_token:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get days parameter (default 30)
        days = request.args.get('days', 30, type=int)
        
        # Count files before cleanup
        pattern = os.path.join(STATIC_DIR, "*_7d.png")
        import glob
        before_count = len(glob.glob(pattern))
        
        # Run cleanup
        _cleanup_old_charts(keep_days=days)
        
        # Count files after cleanup
        after_count = len(glob.glob(pattern))
        removed_count = before_count - after_count
        
        return jsonify({
            'success': True,
            'files_before': before_count,
            'files_after': after_count,
            'files_removed': removed_count,
            'keep_days': days
        }), 200
    except Exception as e:
        print(f"❌ Error in chart cleanup: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trigger/weekly-stocks', methods=['POST'])
def trigger_weekly_stocks():
    """Endpoint to trigger weekly stocks + news collection - for Monday Render cron jobs"""
    # Get auth token from header or query param
    auth_token = request.headers.get('X-Auth-Token') or request.args.get('auth_token')
    expected_token = os.environ.get('CRON_AUTH_TOKEN')
    
    if not expected_token or auth_token != expected_token:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Force Monday behavior even if not Monday (for weekly stocks)
        date = datetime.now()
        original_weekday = date.weekday()
        
        print(f"🔄 Triggered weekly stocks + news collection for {date.strftime('%Y-%m-%d')}")
        
        # Temporarily override weekday check by modifying the date to be Monday
        if original_weekday != 0:
            # Find the most recent Monday
            days_since_monday = (date.weekday() - 0) % 7
            if days_since_monday == 0 and date.hour < 6:  # If it's Monday but before 6am, use last Monday
                days_since_monday = 7
            monday_date = date - timedelta(days=days_since_monday)
            date = monday_date
        
        # Run the digest build with stocks
        payload = build_digest_for_date(date)
        
        return jsonify({
            'success': True,
            'date': payload['date'],
            'sections': {k: len(v) for k, v in payload['sections'].items()},
            'has_stocks': bool(payload.get('stocks_html')),
            'actual_weekday': original_weekday,
            'processed_as_monday': True
        }), 200
    except Exception as e:
        print(f"❌ Error in weekly stocks trigger: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '3000'))
    app.run(host='0.0.0.0', port=port, debug=True) 