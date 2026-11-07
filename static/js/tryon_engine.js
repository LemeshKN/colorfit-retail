// Shared try-on engine: face tracker, camera and the frame overlay.
// Plain script (not a module). It adds one global: window.ColorFitTryOn.
(() => {
  "use strict";

  const VERSION = "0.10.35";
  const BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@" + VERSION;
  const MODEL =
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

  const P = { eyeA: 33, eyeB: 263, nose: 1, cheekL: 234, cheekR: 454 };
  const EYE_OFFSET = 0.05; // lens centre sits a little below the eye-corner line
  const SMOOTH = 0.4; // 0 to 1, higher follows faster but shakes more
  const MIN_INTERVAL = 40; // ms between detections, so at most 25 per second
  const FADE_START = 0.22; // head turn where the frame starts to fade
  const FADE_END = 0.5; // head turn where the frame is gone
  const LOST_AFTER = 300; // ms without a face before the frame hides

  let trackerPromise = null;

  // One tracker for the whole page, started once. Video mode, two faces
  // (the scan needs to spot groups). The try-on later switches to one face.
  function loadTracker() {
    if (!trackerPromise) {
      trackerPromise = (async () => {
        if (typeof WebAssembly !== "object") throw new Error("no WebAssembly");
        const { FaceLandmarker, FilesetResolver } = await import(BASE);
        const fileset = await FilesetResolver.forVisionTasks(BASE + "/wasm");
        const make = (delegate) =>
          FaceLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: MODEL, delegate },
            runningMode: "VIDEO",
            numFaces: 2,
          });
        try {
          return await make("GPU");
        } catch (error) {
          return await make("CPU");
        }
      })().catch((error) => {
        trackerPromise = null;
        throw error;
      });
    }
    return trackerPromise;
  }

  // Front camera, small picture size so slow phones keep up.
  async function openCamera(video) {
    if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("no camera");
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    video.srcObject = stream;
    try {
      await video.play();
    } catch (error) {
      stream.getTracks().forEach((track) => track.stop());
      video.srcObject = null;
      throw error;
    }
    return stream;
  }

  function stopStream(video, stream) {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    video.srcObject = null;
  }

  const api = { loadTracker, openCamera, stopStream, create, P };

  function create(opts) {
    const { stage, video, canvas } = opts;
    const texts = opts.texts || {};
    const debug = !!opts.debug;
    const report = opts.setStatus || function () {};
    const ctx = canvas.getContext("2d");

    let tracker = null;
    let running = false;
    let rafId = 0;
    let frameImg = null;
    let frameFailed = false;
    let factor = 1.6;
    let selectedUrl = null;
    const images = new Map();
    let target = null;
    let cur = null;
    let points = null;
    let lastSeen = 0;
    let lastVideoTime = -1;
    let lastDetectAt = 0;
    let avgDetect = 0;
    let shown = 0;
    let message = null;
    let box = { w: 0, h: 0 };
    let fpsCount = 0;
    let fpsStart = 0;
    let fps = 0;

    function say(msg) {
      if (msg !== message) {
        message = msg;
        report(msg);
      }
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      box = { w: stage.clientWidth, h: stage.clientHeight };
      canvas.width = Math.round(box.w * dpr);
      canvas.height = Math.round(box.h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // Landmarks are 0 to 1 in the camera picture. The video fills the stage
    // with object-fit: cover, so scale and shift them to match the screen.
    function toScreen(point) {
      const vw = video.videoWidth;
      const vh = video.videoHeight;
      const s = Math.max(box.w / vw, box.h / vh);
      return {
        x: point.x * vw * s + (box.w - vw * s) / 2,
        y: point.y * vh * s + (box.h - vh * s) / 2,
      };
    }

    function detectIfDue(now) {
      if (!tracker || video.readyState < 2 || !video.videoWidth) return;
      if (video.currentTime === lastVideoTime) return;
      if (now - lastDetectAt < Math.max(MIN_INTERVAL, avgDetect * 1.1)) return;
      lastVideoTime = video.currentTime;
      lastDetectAt = now;

      const t0 = performance.now();
      let result;
      try {
        result = tracker.detectForVideo(video, t0);
      } catch (error) {
        return;
      }
      const took = performance.now() - t0;
      avgDetect = avgDetect ? avgDetect * 0.8 + took * 0.2 : took;
      fpsCount += 1;
      if (t0 - fpsStart >= 1000) {
        fps = fpsCount;
        fpsCount = 0;
        fpsStart = t0;
      }

      const faces = result.faceLandmarks;
      if (!faces || faces.length === 0) return;
      const lm = faces[0];

      let a = toScreen(lm[P.eyeA]);
      let b = toScreen(lm[P.eyeB]);
      if (a.x > b.x) [a, b] = [b, a];
      const eye = Math.hypot(b.x - a.x, b.y - a.y);
      if (eye < 1) return;
      const angle = Math.atan2(b.y - a.y, b.x - a.x);
      const offset = EYE_OFFSET * eye;

      // Head turn: how uneven the nose sits between the two cheeks.
      const nose = toScreen(lm[P.nose]);
      const cl = toScreen(lm[P.cheekL]);
      const cr = toScreen(lm[P.cheekR]);
      const left = Math.hypot(nose.x - cl.x, nose.y - cl.y);
      const right = Math.hypot(nose.x - cr.x, nose.y - cr.y);
      const turn = left > 0 && right > 0 ? Math.abs(Math.log(left / right)) : 1;
      const alpha = 1 - Math.min(1, Math.max(0, (turn - FADE_START) / (FADE_END - FADE_START)));

      if (now - lastSeen > LOST_AFTER) cur = null;
      target = {
        cx: (a.x + b.x) / 2 - Math.sin(angle) * offset,
        cy: (a.y + b.y) / 2 + Math.cos(angle) * offset,
        w: eye * factor,
        angle,
        alpha,
      };
      lastSeen = now;
      if (debug) points = [a, b, nose, cl, cr];
    }

    function draw(now) {
      ctx.clearRect(0, 0, box.w, box.h);
      const lost = !target || now - lastSeen > LOST_AFTER;

      if (frameFailed) say(texts.frameFailed || "");
      else if (!frameImg) say(texts.frameLoading || "");
      else if (lost) say(texts.lookAt || "");
      else if (target.alpha < 0.5) say(texts.turnBack || "");
      else if (debug) say(fps + " detections/s, " + Math.round(avgDetect) + " ms each");
      else say("");

      if (!target) return;
      if (!cur) cur = { ...target };
      for (const key of ["cx", "cy", "w", "angle"]) cur[key] += (target[key] - cur[key]) * SMOOTH;
      const wanted = lost || !frameImg ? 0 : target.alpha;
      shown += (wanted - shown) * 0.3;

      if (frameImg && shown > 0.02) {
        const w = cur.w;
        const h = (w * frameImg.naturalHeight) / frameImg.naturalWidth;
        ctx.save();
        ctx.globalAlpha = Math.min(1, shown);
        ctx.translate(cur.cx, cur.cy);
        ctx.rotate(cur.angle);
        ctx.drawImage(frameImg, -w / 2, -h / 2, w, h);
        ctx.restore();
      }
      if (debug && points && !lost) {
        ctx.fillStyle = "#ef4444";
        for (const p of points) ctx.fillRect(p.x - 3, p.y - 3, 6, 6);
      }
    }

    function tick() {
      if (!running) return;
      rafId = requestAnimationFrame(tick);
      const now = performance.now();
      detectIfDue(now);
      draw(now);
    }

    // frame = { url, factor }
    function select(frame) {
      selectedUrl = frame.url;
      frameFailed = false;
      factor = Number(frame.factor) || 1.6;
      let img = images.get(frame.url);
      if (!img) {
        img = new Image();
        img.decoding = "async";
        images.set(frame.url, img);
        img.onerror = () => {
          images.delete(frame.url);
          if (selectedUrl === frame.url) frameFailed = true;
        };
        img.src = frame.url;
      }
      if (img.complete && img.naturalWidth) {
        frameImg = img;
      } else {
        frameImg = null;
        img.addEventListener("load", () => {
          if (selectedUrl === frame.url) frameImg = img;
        });
      }
    }

    async function start(frame) {
      tracker = await api.loadTracker();
      try {
        await tracker.setOptions({ numFaces: 1 });
      } catch (error) {
        // keep the current setting, the try-on still works with two faces
      }
      resize();
      target = cur = points = null;
      lastSeen = 0;
      shown = 0;
      lastVideoTime = -1;
      lastDetectAt = 0;
      avgDetect = 0;
      message = null;
      select(frame);
      running = true;
      fpsStart = performance.now();
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(tick);
    }

    function stop() {
      running = false;
      cancelAnimationFrame(rafId);
      ctx.clearRect(0, 0, box.w, box.h);
    }

    if (window.ResizeObserver) new ResizeObserver(resize).observe(stage);
    else window.addEventListener("resize", resize);

    return { start, stop, select, resize };
  }

  window.ColorFitTryOn = api;
})();