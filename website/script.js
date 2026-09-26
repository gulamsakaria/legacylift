(function () {
  "use strict";

  /* ---------- theme toggle (persisted per-browser only, never read back by us) ---------- */
  var root = document.documentElement;
  var themeBtn = document.getElementById("theme-toggle");
  function applyTheme(t) {
    if (t === "light" || t === "dark") root.setAttribute("data-theme", t);
    else root.removeAttribute("data-theme");
    if (themeBtn) themeBtn.textContent = (root.getAttribute("data-theme") === "dark") ? "☀" : "🌙";
  }
  var saved = null;
  try { saved = localStorage.getItem("legacylift-theme"); } catch (e) { /* private mode etc. */ }
  applyTheme(saved);
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme");
      var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      var next;
      if (!current) next = prefersDark ? "light" : "dark";
      else next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      try { localStorage.setItem("legacylift-theme", next); } catch (e) { /* ignore */ }
    });
  }

  /* ---------- real 3D tilt-on-hover ---------- */
  document.querySelectorAll("[data-tilt]").forEach(function (card) {
    card.addEventListener("mousemove", function (e) {
      var r = card.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = "perspective(900px) rotateX(" + (-y * 6).toFixed(2) + "deg) "
        + "rotateY(" + (x * 6).toFixed(2) + "deg) translateZ(4px)";
    });
    card.addEventListener("mouseleave", function () {
      card.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg) translateZ(0px)";
    });
  });

  /* ---------- animated count-up numbers, triggered once visible ---------- */
  function animateCount(el, target, duration) {
    var start = performance.now();
    var decimals = el.dataset.decimals ? parseInt(el.dataset.decimals, 10) : 0;
    function tick(now) {
      var p = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - p, 3);
      var val = target * eased;
      el.textContent = decimals ? val.toFixed(decimals) : Math.round(val);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  var counted = new WeakSet();
  var revealed = new WeakSet();
  var io = ("IntersectionObserver" in window)
    ? new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          if (el.classList.contains("count-up") && !counted.has(el)) {
            counted.add(el);
            animateCount(el, parseFloat(el.dataset.target || "0"), 1000);
          }
          if (el.classList.contains("will-reveal") && !revealed.has(el)) {
            revealed.add(el);
            el.classList.add("in-view", "reveal");
          }
        });
      }, { threshold: 0.35 })
    : null;

  document.querySelectorAll(".count-up").forEach(function (el) {
    if (io) io.observe(el);
    else animateCount(el, parseFloat(el.dataset.target || "0"), 1000); // no-JS-observer fallback
  });
  document.querySelectorAll(".will-reveal").forEach(function (el) {
    if (io) io.observe(el);
    else el.classList.add("in-view");
  });

  /* ---------- copy install command ---------- */
  var copyBtn = document.getElementById("copy-install");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var text = document.getElementById("install-cmd").textContent;
      var done = function () { copyBtn.textContent = "Copied"; setTimeout(function () { copyBtn.textContent = "Copy"; }, 1400); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () { done(); });
      } else {
        done();
      }
    });
  }

  /* ---------- live scan form: drag & drop + submit overlay ---------- */
  var dz = document.getElementById("dropzone");
  var fileInput = document.getElementById("project");
  var dzText = document.getElementById("dz-text");
  if (dz && fileInput) {
    ["dragenter", "dragover"].forEach(function (evt) {
      dz.addEventListener(evt, function (e) { e.preventDefault(); dz.classList.add("drag-over"); });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      dz.addEventListener(evt, function (e) { e.preventDefault(); dz.classList.remove("drag-over"); });
    });
    dz.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        dzText.textContent = e.dataTransfer.files[0].name;
      }
    });
    fileInput.addEventListener("change", function () {
      if (fileInput.files.length) dzText.textContent = fileInput.files[0].name;
    });
  }

  var scanForm = document.getElementById("scan-form");
  var scanOverlay = document.getElementById("scan-overlay");
  var scanStepText = document.getElementById("scan-step");
  var scanBtn = document.getElementById("scan-btn");
  if (scanForm && scanOverlay) {
    scanForm.addEventListener("submit", function () {
      if (!fileInput || !fileInput.files.length) return;
      if (scanBtn) scanBtn.disabled = true;
      scanOverlay.classList.add("show");
      var steps = ["Uploading file…", "Scanning for risk patterns…", "Applying safe fixes…",
                   "Generating tests…", "Verifying & building report…"];
      var i = 0;
      scanStepText.textContent = steps[0];
      setInterval(function () { i = (i + 1) % steps.length; scanStepText.textContent = steps[i]; }, 900);
    });
  }

  /* ---------- mobile nav (simple show/hide, no framework) ---------- */
  var navToggle = document.getElementById("nav-toggle");
  var navLinks = document.getElementById("nav-links");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", function () {
      navLinks.classList.toggle("open");
    });
  }
})();
