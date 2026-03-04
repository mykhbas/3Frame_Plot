# Assignment 1 — Figma Wireframe Plan (3-Frame C-Scan Viewer)

## 1) Page Structure

- **Page name:** `C-Scan Viewer v1`
- **Frame size (Desktop):** `1440 x 900`
- **Layout grid:** 12 columns, margin 32, gutter 24
- **Main sections:**
  1. Header / Toolbar
  2. Control Panel (left)
  3. 3-Frame C-Scan Canvases (center-right)
  4. Status Bar (bottom)

---

## 2) Components (Auto Layout in Figma)

### A. Header / Toolbar
- App Title: `C-Scan 3 Frame Viewer`
- Subtitle: `Mock Data + Excel Import`
- Buttons:
  - `Import Excel`
  - `Reset Mock Data`

### B. Left Control Panel (fixed width ~300)
- Section: `Color & Scale`
  - Dropdown: `Colormap`
    - Options: `viridis`, `plasma`, `inferno`, `magma`, `cividis`, `jet`, `turbo`, `gray`
  - Inputs: `Scale Min`, `Scale Max`
  - Button: `Auto Scale`
- Section: `Data`
  - Label: `Current Source`
  - Label: `Loaded Sheets`
  - Hint text about expected Excel formats

### C. 3 Frame Viewer Area
- 3 cards in one row (responsive wrap allowed):
  - Card 1: `Frame A`
  - Card 2: `Frame B`
  - Card 3: `Frame C`
- Each card contains:
  - Title
  - Heatmap area (1:1 preferred)
  - Mini colorbar strip / scale annotation

### D. Bottom Status Bar
- Left: status text (`Ready`, `Loaded file`, `Error`)
- Right: data info (`shape`, `min/max`)

---

## 3) Interaction Spec

1. **On startup**
   - Show mock data in all 3 frames.
   - Colormap defaults to `viridis`.
   - Scale defaults to global min/max from displayed data.

2. **Import Excel**
   - User chooses `.xlsx` file.
   - App loads first 3 sheets (or first sheet if only one and duplicates to 3 frames).
   - Status bar updates with filename and sheet names.

3. **Colormap change**
   - Applies immediately to all 3 frames.

4. **Scale min/max change**
   - Applies immediately when valid numeric values are entered.
   - If invalid (`min >= max`), show status error and keep previous scale.

5. **Auto Scale**
   - Recomputes min/max from all currently displayed frames.

---

## 4) Data Mapping Spec

- **Mock data:** 3 synthetic 2D arrays (e.g., 128x128) with distinct patterns.
- **Excel parsing strategy:**
  1. Read numeric values only.
  2. If each row length is a perfect square (e.g., 10000), reshape each row to image and average rows.
  3. Else if full matrix size is perfect square, reshape whole matrix.
  4. Else fallback to direct 2D matrix visualization.

---

## 5) Handoff to Coding

- Framework selected: **Python + Tkinter + Matplotlib** (fast prototype and easy deployment).
- Deliverables:
  - GUI with 3 C-Scan panels
  - Mock data startup
  - Excel import
  - Colormap + scale control
  - Status feedback

