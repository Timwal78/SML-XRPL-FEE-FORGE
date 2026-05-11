/**
 * SML XRPL FEE FORGE — RLUSD RAILS Widget v1.0
 *
 * Embeddable RLUSD/XRP checkout button. Drop in any HTML page:
 *
 *   <script src="https://your-rails.com/widget.js"></script>
 *   <div data-rlusd-rails
 *        data-merchant-id="acme-co"
 *        data-merchant-addr="rMerchantAddr..."
 *        data-amount="99.00"
 *        data-currency="RLUSD"
 *        data-description="Pro plan, monthly"
 *        data-api="https://your-rails.com">
 *   </div>
 *
 * Renders a button that opens a payment modal with QR + xrpl: URI deeplink.
 * Polls /api/invoice/{id} until status === "paid" or expired.
 *
 * Stays under 30KB (manifesto requirement). Pure vanilla, no dependencies.
 */

(function () {
  "use strict";

  if (window.__SML_RAILS__) return;
  window.__SML_RAILS__ = true;

  const STYLES = `
    .sml-rails-btn {
      display: inline-flex; align-items: center; gap: 10px;
      padding: 14px 22px; border: 0; border-radius: 10px; cursor: pointer;
      font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 14px;
      font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
      color: #0a0d12;
      background: linear-gradient(135deg, #ffd700 0%, #ff6b35 100%);
      box-shadow: 0 4px 24px rgba(255, 107, 53, 0.35);
      transition: transform .15s ease, box-shadow .15s ease;
    }
    .sml-rails-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 32px rgba(255,107,53,.5); }
    .sml-rails-btn .dot { width: 8px; height: 8px; border-radius: 50%; background: #0a0d12; animation: sml-pulse 1.5s infinite; }
    @keyframes sml-pulse { 0%,100% { opacity: 1; } 50% { opacity: .3; } }
    .sml-rails-modal-bg {
      position: fixed; inset: 0; background: rgba(10,13,18,0.85);
      backdrop-filter: blur(8px); z-index: 999998;
      display: flex; align-items: center; justify-content: center;
      animation: sml-fade .2s ease;
    }
    @keyframes sml-fade { from { opacity: 0; } to { opacity: 1; } }
    .sml-rails-modal {
      background: #0f141b; border: 1px solid #1f2733; border-radius: 16px;
      width: min(440px, calc(100vw - 32px)); padding: 28px;
      font-family: 'JetBrains Mono', ui-monospace, monospace; color: #e6edf3;
      box-shadow: 0 30px 80px rgba(0,0,0,0.6);
      position: relative;
    }
    .sml-rails-modal::before {
      content: ""; position: absolute; top: 0; left: 16px; right: 16px; height: 2px;
      background: linear-gradient(90deg, #ffd700, #ff6b35);
      border-radius: 0 0 4px 4px;
    }
    .sml-rails-close {
      position: absolute; top: 12px; right: 14px; background: transparent;
      border: 0; color: #7d8590; font-size: 22px; cursor: pointer; line-height: 1;
    }
    .sml-rails-close:hover { color: #e6edf3; }
    .sml-rails-brand {
      font-size: 10px; letter-spacing: 0.25em; text-transform: uppercase;
      color: #7d8590; margin-bottom: 4px;
    }
    .sml-rails-brand b { color: #ff6b35; }
    .sml-rails-headline { font-size: 18px; font-weight: 700; margin-bottom: 6px; line-height: 1.3; }
    .sml-rails-blurb { font-size: 12px; color: #9ba3ad; margin-bottom: 18px; line-height: 1.5; }
    .sml-rails-amount {
      background: #161c25; border: 1px solid #1f2733; border-radius: 10px;
      padding: 16px; text-align: center; margin-bottom: 16px;
    }
    .sml-rails-amount .v { font-size: 28px; font-weight: 800; letter-spacing: -0.02em; }
    .sml-rails-amount .c { font-size: 12px; color: #7d8590; letter-spacing: 0.18em; text-transform: uppercase; margin-top: 4px; }
    .sml-rails-qr {
      background: #fff; padding: 14px; border-radius: 10px;
      margin: 0 auto 14px; width: fit-content;
    }
    .sml-rails-qr img { display: block; width: 200px; height: 200px; }
    .sml-rails-row { display: flex; justify-content: space-between; padding: 8px 12px; background: #161c25; border-radius: 6px; font-size: 11px; margin-bottom: 6px; }
    .sml-rails-row .k { color: #7d8590; letter-spacing: 0.1em; text-transform: uppercase; }
    .sml-rails-row .v { font-weight: 600; word-break: break-all; max-width: 60%; text-align: right; }
    .sml-rails-copy { background: transparent; border: 0; color: #58a6ff; cursor: pointer; font-family: inherit; font-size: 10px; }
    .sml-rails-status {
      margin-top: 14px; padding: 12px; border-radius: 8px; text-align: center;
      font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 700;
    }
    .sml-rails-status.pending { background: rgba(255,215,0,.1); color: #ffd700; border: 1px solid rgba(255,215,0,.3); }
    .sml-rails-status.paid { background: rgba(63,185,80,.12); color: #3fb950; border: 1px solid rgba(63,185,80,.3); }
    .sml-rails-status.expired { background: rgba(248,81,73,.12); color: #f85149; border: 1px solid rgba(248,81,73,.3); }
    .sml-rails-status.error { background: rgba(248,81,73,.12); color: #f85149; border: 1px solid rgba(248,81,73,.3); }
    .sml-rails-deeplink { display: block; text-align: center; margin-top: 12px; color: #58a6ff; font-size: 12px; text-decoration: none; }
    .sml-rails-deeplink:hover { text-decoration: underline; }
    .sml-rails-foot { margin-top: 16px; text-align: center; font-size: 9px; letter-spacing: 0.2em; text-transform: uppercase; color: #4a5260; }
  `;

  function injectStyles() {
    if (document.getElementById("sml-rails-styles")) return;
    const s = document.createElement("style");
    s.id = "sml-rails-styles";
    s.textContent = STYLES;
    document.head.appendChild(s);
  }

  function buildXrplUri(destination, tag, amount, currency, issuer) {
    // xrpl:rAddr?dt=12345&amount=10
    // For tokens: xrpl:rAddr?dt=12345&amount=10/RLUSD/issuer
    const params = new URLSearchParams({ dt: String(tag) });
    if (currency === "XRP") {
      params.set("amount", String(amount));
    } else {
      params.set("amount", `${amount}/${currency}/${issuer}`);
    }
    return `xrpl:${destination}?${params.toString()}`;
  }

  function qrUrl(text) {
    // Use chart.googleapis fallback / qrserver.com — both no-API-key public
    return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(text)}`;
  }

  async function createInvoice(api, opts) {
    const r = await fetch(api + "/api/invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        merchant_id: opts.merchantId,
        merchant_addr: opts.merchantAddr,
        amount: parseFloat(opts.amount),
        currency: opts.currency,
        description: opts.description || "",
        ttl_seconds: 1800,
      }),
    });
    if (!r.ok) throw new Error("invoice creation failed: " + r.status);
    return r.json();
  }

  async function pollInvoice(api, id) {
    const r = await fetch(api + "/api/invoice/" + id);
    if (!r.ok) throw new Error("poll failed");
    return r.json();
  }

  function copy(text) {
    navigator.clipboard?.writeText(text).catch(() => {});
  }

  function openModal(api, invoice, opts) {
    const RLUSD_ISSUER = "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"; // mainnet
    const uri = buildXrplUri(
      invoice.destination,
      invoice.destination_tag,
      invoice.amount,
      invoice.currency,
      RLUSD_ISSUER
    );

    const bg = document.createElement("div");
    bg.className = "sml-rails-modal-bg";
    bg.innerHTML = `
      <div class="sml-rails-modal">
        <button class="sml-rails-close">&times;</button>
        <div class="sml-rails-brand">RLUSD <b>RAILS</b> · SML</div>
        <div class="sml-rails-headline">${invoice.headline || "Complete your payment"}</div>
        <div class="sml-rails-blurb">${invoice.blurb || "Pay with any XRPL-compatible wallet"}</div>
        <div class="sml-rails-amount">
          <div class="v">${invoice.amount}</div>
          <div class="c">${invoice.currency}</div>
        </div>
        <div class="sml-rails-qr"><img src="${qrUrl(uri)}" alt="XRPL Pay" /></div>
        <div class="sml-rails-row">
          <span class="k">Destination</span>
          <span class="v">${invoice.destination.slice(0,8)}…${invoice.destination.slice(-6)}
            <button class="sml-rails-copy" data-c="${invoice.destination}">copy</button>
          </span>
        </div>
        <div class="sml-rails-row">
          <span class="k">Tag</span>
          <span class="v">${invoice.destination_tag}
            <button class="sml-rails-copy" data-c="${invoice.destination_tag}">copy</button>
          </span>
        </div>
        <a class="sml-rails-deeplink" href="${uri}">Open in wallet →</a>
        <div class="sml-rails-status pending" id="sml-status">Awaiting payment</div>
        <div class="sml-rails-foot">SML XRPL FEE FORGE</div>
      </div>
    `;
    document.body.appendChild(bg);

    bg.querySelector(".sml-rails-close").onclick = () => bg.remove();
    bg.addEventListener("click", (e) => { if (e.target === bg) bg.remove(); });
    bg.querySelectorAll(".sml-rails-copy").forEach(b =>
      b.onclick = () => { copy(b.getAttribute("data-c")); b.textContent = "copied"; setTimeout(()=>b.textContent="copy", 1200); }
    );

    const statusEl = bg.querySelector("#sml-status");
    let stop = false;
    bg.addEventListener("DOMNodeRemoved", () => stop = true);

    (async function loop() {
      while (!stop) {
        try {
          const s = await pollInvoice(api, invoice.invoice_id);
          if (s.status === "paid") {
            statusEl.className = "sml-rails-status paid";
            statusEl.textContent = "✓ Payment received";
            if (opts.onSuccess) opts.onSuccess(s);
            break;
          } else if (s.status === "expired") {
            statusEl.className = "sml-rails-status expired";
            statusEl.textContent = "Invoice expired";
            break;
          }
        } catch (e) {
          statusEl.className = "sml-rails-status error";
          statusEl.textContent = "Connection error";
        }
        await new Promise(r => setTimeout(r, 3000));
      }
    })();
  }

  async function mount(el) {
    const opts = {
      merchantId: el.getAttribute("data-merchant-id"),
      merchantAddr: el.getAttribute("data-merchant-addr"),
      amount: el.getAttribute("data-amount"),
      currency: (el.getAttribute("data-currency") || "RLUSD").toUpperCase(),
      description: el.getAttribute("data-description") || "",
      api: el.getAttribute("data-api") || "",
    };
    if (!opts.merchantId || !opts.merchantAddr || !opts.amount || !opts.api) {
      el.textContent = "[RAILS: missing config]";
      return;
    }

    const btn = document.createElement("button");
    btn.className = "sml-rails-btn";
    btn.innerHTML = `<span class="dot"></span>Pay ${opts.amount} ${opts.currency}`;
    btn.onclick = async () => {
      btn.disabled = true;
      btn.innerHTML = `<span class="dot"></span>Creating invoice…`;
      try {
        const inv = await createInvoice(opts.api, opts);
        openModal(opts.api, inv, opts);
      } catch (e) {
        btn.innerHTML = "Error — retry";
      } finally {
        setTimeout(() => {
          btn.disabled = false;
          btn.innerHTML = `<span class="dot"></span>Pay ${opts.amount} ${opts.currency}`;
        }, 600);
      }
    };
    el.appendChild(btn);
  }

  function init() {
    injectStyles();
    document.querySelectorAll("[data-rlusd-rails]").forEach(mount);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.SMLRails = { mount, init };
})();
