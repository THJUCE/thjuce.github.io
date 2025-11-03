// ===== Analytics consent banner and loader =====
(function setupAnalyticsConsent() {
  const LS_KEY = 'consent_analytics';
  const consent = localStorage.getItem(LS_KEY);

  function loadMetrika() {
    if (window.ym) return;
    (function (m, e, t, r, i, k, a) {
      m[i] =
        m[i] ||
        function () {
          (m[i].a = m[i].a || []).push(arguments);
        };
      m[i].l = 1 * new Date();
      k = e.createElement(t);
      a = e.getElementsByTagName(t)[0];
      k.async = 1;
      k.src = r;
      a.parentNode.insertBefore(k, a);
    })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');

    // Инициализация с теми же опциями, что были в HTML
    window.ym &&
      window.ym(105090307, 'init', {
        clickmap: true,
        trackLinks: true,
        accurateTrackBounce: true
      });
  }

  function createBanner() {
    const banner = document.createElement('div');
    banner.id = 'consent-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-live', 'polite');
    banner.style.cssText =
      'position:fixed;bottom:0;left:0;right:0;z-index:1002;background:rgba(0,0,0,0.9);color:#fff;padding:1rem;display:flex;justify-content:center;gap:1rem;border-top:1px solid rgba(138,43,226,0.3)';
    banner.innerHTML =
      '<span style="max-width:60%;text-align:center">Мы используем Яндекс.Метрику для улучшения сайта. Согласны на сбор обезличенной статистики?</span>' +
      '<button id="consent-accept" class="btn btn-primary">Да</button>' +
      '<button id="consent-decline" class="btn btn-secondary">Нет</button>';
    document.body.appendChild(banner);

    const accept = banner.querySelector('#consent-accept');
    const decline = banner.querySelector('#consent-decline');
    accept.addEventListener('click', function () {
      localStorage.setItem(LS_KEY, 'accepted');
      banner.remove();
      loadMetrika();
    });
    decline.addEventListener('click', function () {
      localStorage.setItem(LS_KEY, 'declined');
      banner.remove();
    });
  }

  if (consent === 'accepted') {
    loadMetrika();
  } else if (consent !== 'declined') {
    // Показать баннер только если пользователь ещё не выбирал
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', createBanner);
    } else {
      createBanner();
    }
  }
})();

// ===== Utilities =====
function track(eventName, params) {
  try {
    if (window.ym) {
      window.ym(105090307, 'reachGoal', eventName, params || {});
    }
  } catch (_) {}
}

// ===== Section reveal animations =====
(function setupReveal() {
  const sections = document.querySelectorAll('.section');
  if (!('IntersectionObserver' in window)) {
    sections.forEach((s) => s.classList.add('visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  });
  sections.forEach((section) => observer.observe(section));
})();

/**
* Модалка консультации удалена — используем единую Google Form.
* Все CTA "Записаться" ведут на форму Google (встроенный iframe и ссылка).
*/

// ===== Google Form CTA tracking =====
(function setupGoogleFormCta() {
  // Track clicks on any link that opens the Google Form
  const links = document.querySelectorAll('a[href*="docs.google.com/forms"]');
  links.forEach((a) => {
    a.addEventListener('click', () => track('signup_click_google_form'));
  });
})();

/**
 * Чат виджет удалён по требованию.
 * Код и трекинг, связанные с чат‑сообщениями, очищены.
 */

/**
 * Трекинг кликов по ссылкам (без GitHub и без sticky footer).
 */
(function setupLinkTracking() {
  const links = [
    { selector: 'footer .social a[href*="t.me/VibecodingRus_bot"]', goal: 'telegram_click_bot' },
    { selector: 'footer .social a[href*="t.me/artem_369_432"]', goal: 'telegram_click_admin' }
  ];
  links.forEach(({ selector, goal }) => {
    document.querySelectorAll(selector).forEach((a) => {
      a.addEventListener('click', () => track(goal));
    });
  });
})();
// ===== Accessibility: enhance <details> toggles (ARIA) =====
(function enhanceDetailsA11y() {
  const detailsList = document.querySelectorAll('details.faq');
  detailsList.forEach((d) => {
    const summary = d.querySelector('summary');
    if (!summary) return;

    // Make summary act like a button and reflect expanded state
    summary.setAttribute('role', 'button');
    summary.setAttribute('aria-expanded', d.open ? 'true' : 'false');
    summary.setAttribute('tabindex', '0');

    // Sync aria-expanded when the details element toggles
    d.addEventListener('toggle', () => {
      summary.setAttribute('aria-expanded', d.open ? 'true' : 'false');
    });

    // Keyboard support: Enter/Space toggles
    summary.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        d.open = !d.open;
      }
    });
  });
})();

// ===== Reviews: toggle form and moderation message =====
(function setupReviewForm() {
  const btn = document.getElementById('open-review');
  const form = document.getElementById('review-form');
  const msg = document.getElementById('review-msg');

  if (!btn || !form) return;

  // Initially ensure hidden state is respected
  if (form.style.display === '') form.style.display = 'none';

  btn.addEventListener('click', () => {
    const willShow = form.style.display === 'none';
    form.style.display = willShow ? 'block' : 'none';
    btn.textContent = willShow ? 'Скрыть форму' : 'Оставить отзыв';
    try { track('review_form_toggle', { visible: willShow }); } catch (_) {}
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    // Optional: collect values for future backend submission (not sending now)
    const formData = new FormData(form);
    const payload = {
      name: formData.get('name') || '',
      role: formData.get('role') || '',
      text: formData.get('text') || ''
    };

    // Reset and show moderation message
    form.reset();
    if (msg) {
      msg.style.display = 'block';
      msg.textContent = 'Ваш отзыв на модерации.';
      msg.style.color = '#87f1ff';
    }
    try { track('review_submit', { hasText: !!payload.text }); } catch (_) {}

    // Auto-hide the message and form after a short delay
    setTimeout(() => {
      if (msg) msg.style.display = 'none';
      form.style.display = 'none';
      btn.textContent = 'Оставить отзыв';
    }, 3500);
  });
})();