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

  // Home page product showcase: tabs that advance on their own until the visitor picks one.
  // The progress bar's animation drives the timing, so pausing it (hover, focus, off-screen) pauses the advance.
  var sc = document.querySelector('.showcase');
  if (sc) {
    var tabs = [].slice.call(sc.querySelectorAll('.sc-tab'));
    var panels = [].slice.call(sc.querySelectorAll('.sc-panel'));
    var tabList = sc.querySelector('.sc-tabs');
    var current = 0, hovering = false, offscreen = true;
    sc.classList.add('ready');

    function select(i, focus) {
      current = (i + tabs.length) % tabs.length;
      tabs.forEach(function (t, n) {
        var on = n === current;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        panels[n].classList.toggle('is-active', on);
      });
      var t = tabs[current];
      if (tabList.scrollWidth > tabList.clientWidth) tabList.scrollTo({ left: t.offsetLeft - 16, behavior: 'smooth' });
      if (focus) t.focus();
    }
    function stopAuto() { sc.classList.remove('auto'); }
    function syncPause() { sc.classList.toggle('paused', hovering || offscreen); }

    tabs.forEach(function (t, n) {
      t.addEventListener('click', function () { stopAuto(); select(n); });
    });
    tabList.addEventListener('keydown', function (e) {
      var k = e.key, next = null;
      if (k === 'ArrowRight' || k === 'ArrowDown') next = current + 1;
      else if (k === 'ArrowLeft' || k === 'ArrowUp') next = current - 1;
      else if (k === 'Home') next = 0;
      else if (k === 'End') next = tabs.length - 1;
      if (next === null) return;
      e.preventDefault(); stopAuto(); select(next, true);
    });

    // Phones get swipeable tabs only: no progress bar there, so content shouldn't change under the reader.
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && window.matchMedia('(min-width: 861px)').matches) {
      sc.style.setProperty('--sc-ms', '7000ms');
      sc.classList.add('auto');
      sc.addEventListener('animationend', function (e) {
        if (e.animationName === 'sc-fill' && sc.classList.contains('auto')) select(current + 1);
      });
      sc.addEventListener('mouseenter', function () { hovering = true; syncPause(); });
      sc.addEventListener('mouseleave', function () { hovering = false; syncPause(); });
      sc.addEventListener('focusin', function () { hovering = true; syncPause(); });
      sc.addEventListener('focusout', function () { hovering = false; syncPause(); });
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (entries) {
          offscreen = !entries[0].isIntersecting; syncPause();
        }, { threshold: 0.25 }).observe(sc);
      } else { offscreen = false; }
      syncPause();
    }
  }

  // Fade blocks up as they scroll into view. Siblings in a grid are staggered slightly.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('.section-head, .about-media, .about-copy, .svc-card, .cta-copy, .steps li, .stat, .tags, .faq, .marquee, .post-card, .feature-list li, .article-foot').forEach(function (el) {
      var i = [].indexOf.call(el.parentNode.children, el);
      if (i > 0 && i < 6 && !el.matches('.section-head, .faq, .tags, .about-media, .about-copy, .cta-copy')) el.style.setProperty('--rd', (i * 0.08) + 's');
      el.classList.add('reveal');
      io.observe(el);
    });
  }

  // Stats count up from zero the first time they scroll into view. The real number is in the HTML.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var counter = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        counter.unobserve(e.target);
        var el = e.target, to = +el.dataset.count, start = null;
        function step(t) {
          if (!start) start = t;
          var k = Math.min((t - start) / 1400, 1);
          el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))) + '+';
          if (k < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    document.querySelectorAll('.stat-num[data-count]').forEach(function (el) { counter.observe(el); });
  }

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
