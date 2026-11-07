// Result page: "Try on live" opens the camera and puts a frame on the face.
// No video or picture leaves the phone.
(() => {
  "use strict";

  const T = window.ColorFitTryOn;
  const root = document.getElementById("tryon");
  if (!T || !root) return;

  const text = root.dataset;
  const panel = document.getElementById("tryon-panel");
  const stage = document.getElementById("tryon-stage");
  const video = document.getElementById("tryon-video");
  const canvas = document.getElementById("tryon-canvas");
  const statusEl = document.getElementById("tryon-status");
  const noteEl = document.getElementById("tryon-note");
  const openBtn = document.getElementById("tryon-open");
  const closeBtn = document.getElementById("tryon-close");
  const buttons = Array.from(panel.querySelectorAll(".tryon-frame"));
  if (buttons.length === 0) return;
  root.hidden = false;

  const frameOf = (btn) => ({ url: btn.dataset.url, factor: btn.dataset.factor });
  const engine = T.create({
    stage,
    video,
    canvas,
    debug: new URLSearchParams(window.location.search).has("debug"),
    setStatus: (msg) => {
      statusEl.textContent = msg;
    },
    texts: {
      frameFailed: text.textFrameFailed,
      frameLoading: text.textFrameLoading,
      lookAt: text.textLookAt,
      turnBack: text.textTurnBack,
    },
  });

  let session = 0;
  let stream = null;
  let pushed = false;
  let selected = buttons[0];

  // Start loading the tracker while the customer reads the page, unless the
  // phone asks to save data.
  const saveData = navigator.connection && navigator.connection.saveData;
  if (!saveData) {
    const preload = () => T.loadTracker().catch(() => {});
    if ("requestIdleCallback" in window) window.requestIdleCallback(preload, { timeout: 4000 });
    else setTimeout(preload, 2000);
  }

  function mark(btn) {
    selected = btn;
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
  }

  function teardown() {
    session += 1;
    engine.stop();
    T.stopStream(video, stream);
    stream = null;
    panel.hidden = true;
    document.body.classList.remove("tryon-open");
  }

  function close(message) {
    teardown();
    noteEl.textContent = message || "";
    if (pushed) {
      pushed = false;
      history.back();
    }
  }

  async function open() {
    const mine = ++session;
    history.pushState({ colorfitTryon: true }, "");
    pushed = true;
    document.body.classList.add("tryon-open");
    panel.hidden = false;
    noteEl.textContent = "";
    engine.resize();
    statusEl.textContent = text.textOpening;

    const trackerPromise = T.loadTracker();
    trackerPromise.catch(() => {});
    try {
      stream = await T.openCamera(video);
    } catch (error) {
      if (mine === session) close(text.textNoCamera);
      return;
    }
    if (mine !== session) {
      T.stopStream(video, stream);
      stream = null;
      return;
    }
    statusEl.textContent = text.textLoading;
    try {
      await trackerPromise;
    } catch (error) {
      if (mine === session) close(text.textUnsupported);
      return;
    }
    if (mine !== session) return;
    mark(selected);
    try {
      await engine.start(frameOf(selected));
    } catch (error) {
      if (mine === session) close(text.textUnsupported);
      return;
    }
    if (mine !== session) engine.stop();
  }

  openBtn.addEventListener("click", open);
  closeBtn.addEventListener("click", () => close());
  buttons.forEach((btn) =>
    btn.addEventListener("click", () => {
      mark(btn);
      engine.select(frameOf(btn));
    }),
  );
  window.addEventListener("popstate", () => {
    if (panel.hidden) return;
    pushed = false; // the browser already removed our history entry
    close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) close();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && !panel.hidden) close();
  });
  window.addEventListener("pagehide", () => T.stopStream(video, stream));
})();