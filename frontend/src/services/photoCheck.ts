/** Visual photo check. Not a food-safety certificate. Optional remote vision only if VITE_AI_VISION_URL is set. */

export type PhotoCheck = {
  imageClass: "FOOD" | "NON_FOOD" | "UNCERTAIN";
  decision: string;
  blocked: boolean;
  guidance: string;
  source: string;
  issues: string[];
};

function loadImage(file: File) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read photo"));
    };
    img.src = url;
  });
}

function hsv(r: number, g: number, b: number) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  let h = 0;
  if (d) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
    if (h < 0) h += 360;
  }
  return { h, s: max === 0 ? 0 : d / max, v: max };
}

function sample(img: HTMLImageElement) {
  const scale = Math.min(1, 160 / Math.max(img.width, img.height));
  const w = Math.max(24, Math.round(img.width * scale));
  const h = Math.max(24, Math.round(img.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Canvas unavailable");
  ctx.drawImage(img, 0, 0, w, h);
  const data = ctx.getImageData(0, 0, w, h).data;
  const total = w * h;
  let mold = 0;
  let dark = 0;
  let wet = 0;
  let lum = 0;
  let sat = 0;
  let paper = 0;
  let warm = 0;
  let textile = 0;
  let sharp = 0;
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const c = hsv(r, g, b);
    const l = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    lum += l;
    sat += c.s;
    if ((c.h >= 70 && c.h <= 170 && c.s > 0.12 && c.v > 0.25 && c.v < 0.78) || (g > r + 18 && g > b + 8)) mold += 1;
    if (l < 0.14) dark += 1;
    if (c.v > 0.82 && c.s < 0.22) wet += 1;
    if (l > 0.72 && c.s < 0.12) paper += 1;
    if (((c.h >= 5 && c.h <= 55) || c.h >= 350) && c.s > 0.28 && c.v > 0.35) warm += 1;
    if (c.h >= 190 && c.h <= 250 && c.s > 0.15 && c.v > 0.25 && c.v < 0.75) textile += 1;
  }
  for (let y = 4; y < h - 4; y += 4) {
    for (let x = 4; x < w - 4; x += 4) {
      const i = (y * w + x) * 4;
      const here = (data[i] + data[i + 1] + data[i + 2]) / 3;
      const right = (data[i + 16] + data[i + 17] + data[i + 18]) / 3;
      sharp += Math.abs(here - right);
    }
  }
  return {
    mold: mold / total,
    dark: dark / total,
    wet: wet / total,
    lum: lum / total,
    sat: sat / total,
    paper: paper / total,
    warm: warm / total,
    textile: textile / total,
    sharp: sharp / (total / 16),
  };
}

export async function analyzeFoodPhoto(file: File): Promise<PhotoCheck> {
  const endpoint = import.meta.env.VITE_AI_VISION_URL as string | undefined;
  if (endpoint) {
    try {
      const body = new FormData();
      body.append("image", file);
      const res = await fetch(endpoint, { method: "POST", body });
      if (res.ok) {
        const remote = (await res.json()) as Partial<PhotoCheck>;
        if (remote.imageClass && remote.decision) {
          return {
            imageClass: remote.imageClass,
            decision: remote.decision,
            blocked: Boolean(remote.blocked),
            guidance: remote.guidance || "Remote photo check returned no guidance.",
            source: "remote",
            issues: remote.issues || [],
          };
        }
      }
    } catch {
      /* fall through to the on-device visual estimate */
    }
  }

  try {
    const metrics = sample(await loadImage(file));
    if (metrics.paper > 0.42 || (metrics.textile > 0.28 && metrics.warm < 0.08)) {
      return {
        imageClass: "NON_FOOD",
        decision: "Non-food",
        blocked: true,
        guidance: "This photo does not look like food. Retake a photo of the sealed food.",
        source: "visual-estimate",
        issues: ["Does not look like food"],
      };
    }
    if (metrics.lum < 0.18 || metrics.sharp < 4) {
      return {
        imageClass: "UNCERTAIN",
        decision: "Needs review",
        blocked: true,
        guidance: "The photo is too dark or unclear. Retake it in better light.",
        source: "visual-estimate",
        issues: ["Too dark or unclear"],
      };
    }
    const issues: string[] = [];
    if (metrics.mold > 0.035) issues.push("Possible spoilage colours");
    if (metrics.wet > 0.12) issues.push("Possible leakage");
    if (metrics.lum < 0.22) issues.push("Low light");
    return {
      imageClass: "FOOD",
      decision: issues.length ? "Needs review" : "No obvious visible spoilage",
      blocked: issues.length > 0,
      guidance: issues.length
        ? `${issues.join(". ")}. This is a visual estimate, not a safety certificate.`
        : "No obvious visible spoilage. This is a visual estimate, not a safety certificate.",
      source: "visual-estimate",
      issues,
    };
  } catch {
    return {
      imageClass: "UNCERTAIN",
      decision: "Needs review",
      blocked: true,
      guidance: "The photo could not be read. Try another image.",
      source: "visual-estimate",
      issues: ["Unreadable photo"],
    };
  }
}
