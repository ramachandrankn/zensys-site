(function () {
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  // Mobile menu
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('site-nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.textContent = open ? 'Close' : 'Menu';
    });
  }

  // Shadow under the sticky header once the page has scrolled
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () { header.classList.toggle('scrolled', window.scrollY > 40); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Cookie notice
  var cookie = document.getElementById('cookie');
  if (cookie && store.get('zs-cookie') !== 'ok') {
    cookie.hidden = false;
    cookie.querySelector('button').addEventListener('click', function () {
      store.set('zs-cookie', 'ok');
      cookie.hidden = true;
    });
  }

  // Third-party scripts (PageSense, SalesIQ chat) load after the first interaction
  // or a few seconds after load, so they never block the page.
  var cfg = window.ZS || {};
  var loaded = false;
  function loadThirdParty() {
    if (loaded) return; loaded = true;
    if (cfg.pagesense) {
      var p = document.createElement('script'); p.src = cfg.pagesense; p.async = true; document.head.appendChild(p);
    }
    if (cfg.salesiq) {
      window.$zoho = window.$zoho || {};
      window.$zoho.salesiq = window.$zoho.salesiq || { ready: function () {} };
      var s = document.createElement('script'); s.id = 'zsiqscript';
      s.src = 'https://salesiq.zohopublic.in/widget?wc=' + cfg.salesiq; s.defer = true;
      document.body.appendChild(s);
    }
  }
  ['pointerdown', 'keydown', 'scroll', 'touchstart'].forEach(function (ev) {
    window.addEventListener(ev, loadThirdParty, { once: true, passive: true });
  });
  window.addEventListener('load', function () { setTimeout(loadThirdParty, 4000); });

  // Enquiry form
  document.querySelectorAll('form.enquiry').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (form.querySelector('.hp input').value) { e.preventDefault(); return; }
      if (form.getAttribute('action')) return; // posts to the configured endpoint
      e.preventDefault();
      var f = new FormData(form);
      var body = [
        'Name: ' + (f.get('name') || ''),
        'Company: ' + (f.get('company') || ''),
        'Phone: ' + (f.get('phone') || ''),
        'Email: ' + (f.get('email') || ''),
        'Interested in: ' + (f.get('interest') || ''),
        '',
        f.get('message') || ''
      ].join('\n');
      var subject = 'Enquiry: ' + (f.get('interest') || 'Zensys') + ' — ' + (f.get('company') || f.get('name') || '');
      window.location.href = 'mailto:' + form.dataset.email + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
      var st = form.querySelector('.form-status');
      if (st) st.textContent = 'Your email app should open with the enquiry filled in. If it doesn’t, call or WhatsApp us on ' + form.dataset.phone + '.';
    });
  });

  // "What brings you here?" links pre-select the matching option in the enquiry form
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-interest]'); if (!a) return;
    var sel = document.querySelector('.enquiry select[name=interest]');
    if (sel) sel.value = a.getAttribute('data-interest');
  });

  // Blog filter
  var filter = document.querySelector('.filter');
  if (filter) {
    var cards = document.querySelectorAll('.post-card[data-cat]');
    filter.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      filter.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      var cat = b.dataset.cat;
      cards.forEach(function (c) { c.hidden = cat !== 'all' && c.dataset.cat !== cat; });
    });
  }
})();
