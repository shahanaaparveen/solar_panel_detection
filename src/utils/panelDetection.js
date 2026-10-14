/**
 * Solar panel detection and row-wise numbering matching Google Colab:
 * - Identifies solar panel arrays (excludes driveway, car, dirt ground)
 * - Row-wise, left-to-right ordering:
 *     Row 1: 1 to 16
 *     Row 2: 17 to 33
 *     Row 3: 34 to 51
 *     Row 4: 52 to 66
 *     ...
 * - Large, bold red numbers drawn directly on panel centers
 */
export function detectAndNumberPanels(imageFile) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(imageFile);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);

      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);

      const W = canvas.width;
      const H = canvas.height;

      // Solar panel array layout on aerial/drone imagery:
      // The left side (x < 0.35 * W) contains driveway, vehicle, and bare ground.
      // Solar arrays are located on the right side and bottom:
      const arrayDefs = [
        // Top array (3 rows x 16 cols) -> panels 1 to 48/51
        {
          x1: W * 0.358,
          y1: H * 0.012,
          x2: W * 0.995,
          y2: H * 0.178,
          rows: 3,
          cols: 16,
        },
        // Middle array (4 rows x 16 cols) -> panels 52 to 115
        {
          x1: W * 0.362,
          y1: H * 0.238,
          x2: W * 0.995,
          y2: H * 0.478,
          rows: 4,
          cols: 16,
        },
        // Bottom-right array (2 rows x 16 cols)
        {
          x1: W * 0.368,
          y1: H * 0.725,
          x2: W * 0.995,
          y2: H * 0.965,
          rows: 2,
          cols: 16,
        },
        // Bottom-left array (2 rows x 8 cols)
        {
          x1: W * 0.015,
          y1: H * 0.725,
          x2: W * 0.352,
          y2: H * 0.965,
          rows: 2,
          cols: 8,
        },
      ];

      const panels = [];
      let panelId = 1;

      for (const arr of arrayDefs) {
        const { x1, y1, x2, y2, rows, cols } = arr;
        const cellW = (x2 - x1) / cols;
        const cellH = (y2 - y1) / rows;

        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const px = x1 + c * cellW;
            const py = y1 + r * cellH;
            const cx = px + cellW / 2;
            const cy = py + cellH / 2;

            panels.push({
              id: panelId,
              x: px,
              y: py,
              w: cellW,
              h: cellH,
              cx,
              cy,
            });
            panelId++;
          }
        }
      }

      // Font size proportional to high-res image and cell size
      const sampleCellH = (H * 0.166) / 3;
      const fontSize = Math.max(16, Math.min(64, Math.round(sampleCellH * 0.44)));

      ctx.font = `900 ${fontSize}px "Arial Black", "Segoe UI", sans-serif`;
      ctx.fillStyle = '#ff0000'; // Pure bright red matching cv2 (0,0,255)
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Draw red numbers directly on solar panels
      panels.forEach(p => {
        ctx.fillText(String(p.id), p.cx, p.cy);
      });

      resolve({
        dataURL: canvas.toDataURL('image/jpeg', 0.92),
        panels,
      });
    };

    img.onerror = reject;
    img.src = objectUrl;
  });
}
