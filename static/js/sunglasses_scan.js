const root = document.getElementById("scan");
const cfg = root.dataset;
const statusEl = document.getElementById("scan-status");

const VERSION = "0.10.35";
const BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@" + VERSION;
const MODEL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const MAX_SIDE = 1000;
const MIN_FACE_SHARE = 0.2;
const TURN_RANGE = [0.75, 1.35];
const MAX_ROLL = 30;

const P = {
  top: 10, chin: 152, foreL: 54, foreR: 284, cheekL: 234,
  cheekR: 454, jawL: 172, jawR: 397, nose: 1, eyeL: 33, eyeR: 263,
};

let toolPromise = null;

function setStatus(text) {
  statusEl.textContent = text;
}

function go(reason) {
  window.location.href = cfg.unclearUrl + "?reason=" + reason;
}

function loadTool() {
  if (!toolPromise) {
    toolPromise = (async () => {
      if (typeof WebAssembly !== "object") throw new Error("no WebAssembly");
      const { FaceLandmarker, FilesetResolver } = await import(BASE);
      const fileset = await FilesetResolver.forVisionTasks(BASE + "/wasm");
      return FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL },
        runningMode: "IMAGE",
        numFaces: 2,
      });
    })().catch((error) => {
      toolPromise = null;
      throw error;
    });
  }
  return toolPromise;
}

async function toCanvas(file) {
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas;
  } finally {
    URL.revokeObjectURL(url);
  }
}

// Returns {reason} for a photo we cannot use, or {numbers} for the four distances.
function measure(faces, width, height) {
  if (faces.length === 0) return { reason: "no_face" };
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

async function processCanvas(canvas) {
  setStatus(cfg.textChecking);
  let tool;
  try {
    tool = await loadTool();
  } catch (error) {
    return go("unsupported");
  }
  let result;
  try {
    result = measure(tool.detect(canvas).faceLandmarks, canvas.width, canvas.height);
  } catch (error) {
    return go("unreadable");
  }
  if (result.reason) return go(result.reason);

  try {
    const response = await fetch(cfg.apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.numbers),
    });
    if (!response.ok) return go(response.status === 404 ? "unsupported" : "unreadable");
    const data = await response.json();
    const query = new URLSearchParams({ source: "photo" });
    if (data.alternative) query.set("also", data.alternative.slug);
    window.location.href =
      cfg.shapeUrl.replace("SLUG", data.shape.slug) + "?" + query.toString();
  } catch (error) {
    go("unreadable");
  }
}

async function handleFile(input) {
  const file = input.files[0];
  input.value = "";
  if (!file) return;
  setStatus(cfg.textChecking);
  let canvas;
  try {
    canvas = await toCanvas(file);
  } catch (error) {
    return go("unreadable");
  }
  return processCanvas(canvas);
}

// In-page front camera. If it is not available or not allowed, use the file picker.
const cam = document.getElementById("cam");
const video = document.getElementById("cam-video");
let stream = null;

function stopCamera() {
  if (stream) stream.getTracks().forEach((track) => track.stop());
  stream = null;
  cam.style.display = "none";
}

async function openCamera() {
  setStatus(cfg.textPrepare);
  loadTool().catch(() => {});
  const fallback = () => {
    setStatus("");
    document.getElementById("photo-take").click();
  };
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return fallback();
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
  } catch (error) {
    stopCamera();
    return fallback();
  }
  cam.style.display = "flex";
}

document.getElementById("cam-open").addEventListener("click", openCamera);
document.getElementById("cam-cancel").addEventListener("click", () => {
  stopCamera();
  setStatus("");
});
document.getElementById("cam-shoot").addEventListener("click", async () => {
  const w = video.videoWidth;
  const h = video.videoHeight;
  if (!w || !h) return;
  const scale = Math.min(1, MAX_SIDE / Math.max(w, h));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(w * scale);
  canvas.height = Math.round(h * scale);
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  stopCamera();
  await processCanvas(canvas);
});

document.querySelectorAll("#scan label").forEach((label) => {
  label.addEventListener("click", () => {
    setStatus(cfg.textPrepare);
    loadTool().catch(() => {});
  });
});
document.querySelectorAll('#scan input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => handleFile(input));
});