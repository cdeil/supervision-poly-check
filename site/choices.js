"use strict";

const element = (id) => document.getElementById(id);
const area = (mask) => mask.reduce((sum, pixel) => sum + pixel, 0);
const difference = (a, b) => a.reduce((sum, pixel, i) => sum + (pixel !== b[i]), 0);

function plot(mask, polygon, quantized, title) {
  const cell = 23;
  const margin = 8;
  const side = 8 * cell;
  const point = ([x, y]) => `${margin + x * cell},${margin + y * cell}`;
  let svg = `<svg viewBox="0 0 ${side + margin * 2} ${side + margin * 2}" role="img"><title>${title}</title>`;
  mask.forEach((pixel, i) => {
    const x = margin + (i % 8) * cell;
    const y = margin + Math.floor(i / 8) * cell;
    svg += `<rect x="${x}" y="${y}" width="${cell}" height="${cell}" fill="${pixel ? "#91c4b9" : "#fff"}" stroke="#d5dfda" stroke-width=".65"/>`;
    svg += `<circle cx="${x + cell / 2}" cy="${y + cell / 2}" r="1" fill="#55646b" opacity=".6"/>`;
  });
  if (polygon) {
    svg += `<polygon points="${polygon.map(point).join(" ")}" fill="none" stroke="#1c2635" stroke-width="1.5"/>`;
  }
  if (quantized) {
    const centres = quantized.map(([x, y]) => [x + .5, y + .5]);
    svg += `<polygon points="${centres.map(point).join(" ")}" fill="none" stroke="#8360ab" stroke-dasharray="3 2" stroke-width="1.3"/>`;
    centres.forEach(([x, y]) => {
      svg += `<circle cx="${margin + x * cell}" cy="${margin + y * cell}" r="1.8" fill="#8360ab"/>`;
    });
  }
  return svg + "</svg>";
}

function showData(data) {
  function render() {
    const current = data.cases.find((item) => item.id === element("shape").value);
    const sample = current.samples[Number(element("offset").value)];
    element("offset-value").textContent = `+${sample.offset.toFixed(2)} px`;
    const panels = [
      ["coco", sample.coco, null, "COCO reference"],
      ["sv", sample.supervision, sample.rounded, "Supervision COCO loader"],
      ["trunc", sample.opencvTruncated, sample.truncated, "OpenCV with truncated vertices"],
    ];
    for (const [id, mask, vertices, title] of panels) {
      element(`${id}-area`).textContent = area(mask);
      element(`${id}-plot`).innerHTML = plot(mask, sample.polygon, vertices, `${title}: ${area(mask)} filled pixels`);
      if (id !== "coco") {
        const extra = mask.reduce((sum, pixel, i) => sum + (pixel && !sample.coco[i]), 0);
        const missing = mask.reduce((sum, pixel, i) => sum + (!pixel && sample.coco[i]), 0);
        element(`${id}-difference`).textContent = `${extra} extra · ${missing} missing vs COCO`;
      }
    }
    const delta = difference(sample.supervision, sample.opencvTruncated);
    element("comparison").textContent = delta
      ? `Rounding and truncation differ at ${delta} pixels here, despite using the same integer-fill backend.`
      : "Rounding and truncation match here. Try the square at +0.65 px.";
  }
  element("shape").addEventListener("change", render);
  element("offset").addEventListener("input", render);
  render();

  function renderRoundTrip() {
    const roundTrip = data.roundTrips.find((item) => item.id === element("roundtrip-case").value);
    for (const [id, mask, title] of [
      ["source", roundTrip.source, "Original mask"],
      ["reload", roundTrip.supervision, "Current export and import"],
      ["reference-reload", roundTrip.coco, "Current export and COCO import"],
      ["rle", roundTrip.rle, "RLE export and reload"],
    ]) {
      element(`${id}-area`).textContent = area(mask);
      element(`${id}-plot`).innerHTML = plot(mask, null, null, `${title}: ${area(mask)} filled pixels`);
    }
    const messages = {
      rectangle: "Additional loss: 16 → 16 today, but 16 → 9 if only import changes. RLE keeps all 16 pixels.",
      pixel: "Existing loss: export produces no polygon, so neither importer can recover the pixel. RLE preserves it.",
      hole: "Existing loss: forced instance-polygon export fills the hole. COCO import also changes the boundary; RLE preserves the original mask.",
    };
    element("roundtrip-result").textContent = messages[roundTrip.id];
  }
  element("roundtrip-case").addEventListener("change", renderRoundTrip);
  renderRoundTrip();
}

fetch("choices.json")
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(showData)
  .catch(() => {
    element("roundtrip-result").textContent = "Could not load measured masks. Serve through HTTP and reload; choices.json contains the raw data.";
  });
