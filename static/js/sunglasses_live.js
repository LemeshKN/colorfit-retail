// Scan page: front camera, oval guide, countdown, face check, then the live
// try-on on the same page and the same camera. Nothing is uploaded except the
// four measurement numbers.
(() => {
  "use strict";

  const T = window.ColorFitTryOn;
  const root = document.getElementById("live");
  const openBtn = document.getElementById("cam-open");
  const photoTake = document.getElementById("photo-take");
  if (!T || !root || !openBtn) return;

  const cfg = root.dataset;
  const pageStatus = document.getElementById("scan-status");
  const stage = document.getElementById("live-stage");
  const video = document.getElementById("live-video");
  const canvas = document.getElementById("live-canvas");
  const guide = document.getElementById("live-guide");
  const count = document.getElementById("live-count");
  const statusEl = document.getElementById("live-status");
  const closeBtn = document.getElementById("live-close");
  const startBtn = document.getElementById("live-start");
  const controls = document.getElementById("live-controls");
  const grid = document.getElementById("live-grid");

  const MIN_FACE_SHARE = 0.2;
  const TURN_RANGE = [0.75, 1.35];
  const MAX_ROLL = 30;
  const COUNTDOWN_SECONDS = 2;
  const P = {
    top: 10, chin: 152, foreL: 54, foreR: 284, cheekL: 234,
    cheekR: 454, jawL: 172, jawR: 397, nose: 1, eyeL: 33, eyeR: 263,
  };
  const REASONS = {
    no_face: cfg.textNoFace,
    many_faces: cfg.textManyFaces,
    turned: cfg.textTurned,
    small: cfg.textSmall,
    cut_off: cfg.textCutOff,
    unreadable: cfg.textUnreadable,
  };

  function setStatus(msg) {
    statusEl.textContent = msg;
  }

  const engine = T.create({
    stage,
    video,
    canvas,
    debug: new URLSearchParams(window.location.search).has("debug"),
    setStatus,
    texts: {
      frameFailed: cfg.textFrameFailed,
      frameLoading: cfg.textFrameLoading,
      lookAt: cfg.textLookAt,
      turnBack: cfg.textTurnBack,
    },
  });

  let session = 0;
  let phase = "scan"; // "scan" then "tryon"
  let stream = null;
  let tracker = null;
  let timer = 0;
  let busy = false;
  let pushed = false;
  let detailsUrl = "";

  function stopCamera() {
    T.stopStream(video, stream);
    stream = null;
  }

  function teardown() {
    session += 1;
    clearInterval(timer);
    engine.stop();
    stopCamera();
    root.hidden = true;
    guide.classList.remove("scanning");
    document.body.classList.remove("tryon-open");
  }

  // Close the panel and stay on this page, with an optional message.
  function cancel(message) {
    teardown();
    pageStatus.textContent = message || "";
    if (pushed) {
      pushed = false;
      history.back();
    }
  }

  function goDetails(replace) {
    const url = detailsUrl;
    const wasPushed = pushed;
    pushed = false;
    teardown();
    if (wasPushed && replace) window.location.replace(url);
    else window.location.href = url;
  }

  // Same checks as the old photo scan. Returns { reason } or { numbers }.
  function measure(faces, width, height) {
    if (!faces || faces.length === 0) return { reason: "no_face" };
    if (faces.length > 1) return { reason: "many_faces" };
    const lm = faces[0];
    if (!lm.every((p) => p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1)) {
      return { reason: "cut_off" };
    }
    const pt = (name) => ({ x: lm[P[name]].x * width, y: lm[P[name]].y * height });
    const dist = (a, b) => Math.hypot(pt(a).x - pt(b).x, pt(a).y - pt(b).y);

    const cheek = dist("cheekL", "cheekR");
    if (cheek / width < MIN_FACE_SHARE) return { reason: "small" };
    const turn = dist("nose", "cheekL") / dist("nose", "cheekR");
    const roll =
      (Math.atan2(pt("eyeR").y - pt("eyeL").y, pt("eyeR").x - pt("eyeL").x) * 180) / Math.PI;
    if (turn < TURN_RANGE[0] || turn > TURN_RANGE[1] || Math.abs(roll) > MAX_ROLL) {
      return { reason: "turned" };
    }
    return {
      numbers: {
        face_length: dist("top", "chin"),
        forehead_width: dist("foreL", "foreR"),
        cheekbone_width: cheek,
        jaw_width: dist("jawL", "jawR"),
      },
    };
  }

  function measureNow() {
    if (!video.videoWidth) return { reason: "unreadable" };
    try {
      const result = tracker.detectForVideo(video, performance.now());
      return measure(result.faceLandmarks, video.videoWidth, video.videoHeight);
    } catch (error) {
      return { reason: "unreadable" };
    }
  }

  function retry(reason) {
    busy = false;
    guide.classList.remove("scanning");
    startBtn.disabled = false;
    startBtn.textContent = cfg.textStart;
    setStatus(REASONS[reason] || REASONS.unreadable);
  }

  function buildGrid(frames) {
    grid.textContent = "";
    frames.forEach((frame, index) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tryon-frame";
      btn.setAttribute("aria-pressed", String(index === 0));
      const img = document.createElement("img");
      img.src = frame.thumb || "";
      img.alt = "";
      img.width = 80;
      img.height = 40;
      const label = document.createElement("span");
      label.textContent = frame.name;
      btn.append(img, label);
      btn.addEventListener("click", () => {
        grid.querySelectorAll(".tryon-frame").forEach((b) =>
          b.setAttribute("aria-pressed", String(b === btn)),
        );
        engine.select(frame);
      });
      li.append(btn);
      grid.append(li);
    });
    grid.hidden = false;
  }

  async function showTryOn(data) {
    const mine = session;
    const query = new URLSearchParams({ source: "photo" });
    if (data.alternative) query.set("also", data.alternative.slug);
    detailsUrl = cfg.shapeUrl.replace("SLUG", data.shape.slug) + "?" + query.toString();

    const frames = (data.frames || [])
      .filter((f) => f.tryon_image_url)
      .map((f) => ({
        url: f.tryon_image_url,
        factor: f.tryon_width_factor,
        name: f.name,
        thumb: f.image_url,
      }));
    if (frames.length === 0) {
      goDetails(true);
      return;
    }

    phase = "tryon";
    guide.classList.remove("scanning");
    guide.hidden = true;
    controls.hidden = true;
    count.hidden = true;
    closeBtn.textContent = cfg.textDone;
    buildGrid(frames);
    setStatus("");
    try {
      await engine.start(frames[0]);
    } catch (error) {
      if (mine === session) goDetails(true);
      return;
    }
    if (mine !== session) engine.stop();
  }

  async function capture(mine) {
    setStatus(cfg.textChecking);
    const result = measureNow();
    if (result.reason) {
      retry(result.reason);
      return;
    }
    let data;
    try {
      const response = await fetch(cfg.apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result.numbers),
      });
      if (mine !== session) return;
      if (!response.ok) {
        if (response.status === 404) cancel(cfg.textUnsupported);
        else retry("unreadable");
        return;
      }
      data = await response.json();
    } catch (error) {
      if (mine === session) retry("unreadable");
      return;
    }
    if (mine !== session) return;
    showTryOn(data);
  }

  function startCountdown() {
    if (phase !== "scan" || busy || !tracker) return;
    busy = true;
    startBtn.disabled = true;
    guide.classList.add("scanning");
    const mine = session;
    let n = COUNTDOWN_SECONDS;
    count.hidden = false;
    count.textContent = String(n);
    setStatus(cfg.textHold);
    timer = setInterval(() => {
      if (mine !== session) {
        clearInterval(timer);
        return;
      }
      n -= 1;
      if (n > 0) {
        count.textContent = String(n);
        return;
      }
      clearInterval(timer);
      count.hidden = true;
      capture(mine);
    }, 1000);
  }

  async function open() {
    // No secure camera (plain http or an old browser): use the phone's own
    // camera app through the file picker, as before.
    if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      if (photoTake) photoTake.click();
      return;
    }
    const mine = ++session;
    phase = "scan";
    busy = false;
    tracker = null;
    history.pushState({ colorfitLive: true }, "");
    pushed = true;
    document.body.classList.add("tryon-open");
    root.hidden = false;
    guide.hidden = false;
    guide.classList.remove("scanning");
    count.hidden = true;
    controls.hidden = false;
    grid.hidden = true;
    grid.textContent = "";
    startBtn.disabled = true;
    startBtn.textContent = cfg.textGetting;
    closeBtn.textContent = cfg.textCancel;
    pageStatus.textContent = "";
    engine.resize();
    setStatus(cfg.textOpening);

    // Camera and tracker start together, so neither waits for the other.
    const trackerPromise = T.loadTracker();
    trackerPromise.catch(() => {});
    try {
      stream = await T.openCamera(video);
    } catch (error) {
      if (mine === session) cancel(cfg.textNoCamera);
      return;
    }
    if (mine !== session) {
      stopCamera();
      return;
    }
    setStatus(cfg.textReady);
    try {
      tracker = await trackerPromise;
    } catch (error) {
      if (mine === session) cancel(cfg.textUnsupported);
      return;
    }
    if (mine !== session) return;
    startBtn.disabled = false;
    startBtn.textContent = cfg.textStart;
  }

  openBtn.addEventListener("click", open);
  startBtn.addEventListener("click", startCountdown);
  closeBtn.addEventListener("click", () => {
    if (phase === "tryon") goDetails(true);
    else cancel();
  });
  window.addEventListener("popstate", () => {
    if (root.hidden) return;
    pushed = false; // the browser already removed our history entry
    if (phase === "tryon") goDetails(false);
    else cancel();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden || root.hidden) return;
    if (phase === "tryon") goDetails(true);
    else cancel();
  });
  window.addEventListener("pagehide", stopCamera);
})();