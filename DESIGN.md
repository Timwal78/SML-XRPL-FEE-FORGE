# DESIGN.md — SML XRPL FEE FORGE Design System

> Agent-friendly design reference. Source of truth: [Google Stitch project 294283250106200241](https://stitch.withgoogle.com/projects/294283250106200241).
> Use the `stitch` MCP tool (configured in `.claude/settings.json`) to pull live screens and export tokens directly.

---

## Brand Identity

**Brand voice:** Institutional finance-grade. Precision. Speed. No noise.  
**Aesthetic:** Dark terminal with orange/gold fire — Bloomberg meets crypto rails.

---

## Color Tokens

### Backgrounds

| Token | Hex | Use |
|-------|-----|-----|
| `--bg` | `#0a0d12` | Page background |
| `--bg-elev` | `#0f141b` | Elevated surfaces (cards, panels) |
| `--bg-elev-2` | `#161c25` | Double-elevated (table headers, nested panels) |

### Borders & Lines

| Token | Hex | Use |
|-------|-----|-----|
| `--line` | `#1f2733` | All borders, dividers, table rows |

### Text

| Token | Hex | Use |
|-------|-----|-----|
| `--text` | `#e6edf3` | Primary body text |
| `--text-dim` | `#7d8590` | Labels, metadata, secondary content |

### Accents

| Token | Hex | Use |
|-------|-----|-----|
| `--accent` | `#ff6b35` | Primary CTA, fire highlight |
| `--accent-2` | `#ffd700` | Gold/premium accent, section headers |

### Semantic

| Token | Hex | Use |
|-------|-----|-----|
| `--green` | `#3fb950` | Paid / success states |
| `--red` | `#f85149` | Error / failed states |
| `--blue` | `#58a6ff` | Links, external references |

### Gradients

```css
/* Ambient page glow */
background:
  radial-gradient(1200px 600px at 80% -10%, rgba(255,107,53,0.10), transparent 60%),
  radial-gradient(900px 500px at 10% 110%, rgba(255,215,0,0.06), transparent 60%);

/* CTA / primary button */
background: linear-gradient(135deg, var(--accent-2), var(--accent));

/* Hero text gradient */
background: linear-gradient(135deg, #ffd700, #ff6b35);
-webkit-background-clip: text;
color: transparent;
```

---

## Typography

### Font Stack

| Role | Family | Weights |
|------|--------|---------|
| Display / Headings | `Space Grotesk` | 400, 500, 600, 700, 800 |
| Data / Monospace | `JetBrains Mono` | 400, 500, 700, 800 |
| System fallback | `ui-monospace, monospace` | — |

### Scale

| Label | Size | Font | Weight | Letter-spacing | Use |
|-------|------|------|--------|----------------|-----|
| `brand` | 22px | Space Grotesk | 800 | 0.04em | Brand mark |
| `hero-h1` | 48px | Space Grotesk | 700 | -0.02em | Hero headline |
| `section-title` | 13px | Space Grotesk | 700 | 0.2em | Section labels (ALL CAPS) |
| `stat-value` | 22px | JetBrains Mono | 700 | -0.01em | Dashboard metrics |
| `stat-label` | 10px | JetBrains Mono | 400 | 0.18em | Metric labels (ALL CAPS) |
| `table-header` | 10px | JetBrains Mono | 600 | 0.12em | Column heads (ALL CAPS) |
| `table-body` | 12–13px | JetBrains Mono | 400 | — | Table data |
| `pill` | 10px | JetBrains Mono | 400 | 0.2em | Status pills (ALL CAPS) |
| `button` | 11px | JetBrains Mono | 400–700 | 0.15em | Button labels (ALL CAPS) |

---

## Spacing Scale

| Token | Value | Use |
|-------|-------|-----|
| `xs` | 4px | Tight padding (pills, badges) |
| `sm` | 8–10px | Table cell padding, icon margins |
| `md` | 14–18px | Card interior padding |
| `lg` | 24–28px | Card padding, section margins |
| `xl` | 32–40px | Page padding, product section padding |
| `2xl` | 60–80px | Hero / section vertical breathing room |

---

## Component Patterns

### Stat Card

```css
.stat {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  padding: 18px 20px;
  position: relative;
}
/* Gold-to-orange top accent bar */
.stat::before {
  content: ""; position: absolute;
  top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--accent-2), var(--accent));
  opacity: 0.7;
}
```

**Anatomy:** `LABEL` (10px ALL CAPS dim) → `VALUE` (22px bold) + `unit` (12px dim)

### Section Title

```css
.section-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--text-dim);
  display: flex; align-items: center; gap: 12px;
}
.section-title::before { content: "▌"; color: var(--accent-2); }
.section-title::after  { content: ""; flex: 1; height: 1px; background: var(--line); }
```

### Table

- Container: `--bg-elev` background, `1px solid --line` border
- Headers: `--bg-elev-2`, `10px` ALL CAPS, `--text-dim`, `0.12em` letter-spacing
- Rows: `12px`, hover → `--bg-elev-2` background
- Row divider: `1px solid --line`

### Button

```css
/* Ghost button */
.btn {
  background: var(--bg-elev); border: 1px solid var(--line);
  padding: 8px 14px; color: var(--text);
  font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase;
}
.btn:hover { border-color: var(--accent-2); color: var(--accent-2); }

/* Primary CTA */
.btn-primary {
  background: linear-gradient(135deg, var(--accent-2), var(--accent));
  color: var(--bg); border: 0; font-weight: 700;
}
```

### Network / Status Pill

```css
.network-pill {
  background: var(--bg-elev); border: 1px solid var(--line);
  padding: 4px 12px; font-size: 10px;
  letter-spacing: 0.2em; text-transform: uppercase; color: var(--text-dim);
}
.network-pill.live { border-color: var(--green); color: var(--green); }
```

### Ambient Background Effect

```css
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(1200px 600px at 80% -10%, rgba(255,107,53,0.10), transparent 60%),
    radial-gradient(900px 500px at 10% 110%, rgba(255,215,0,0.06), transparent 60%);
}
/* Optional scan-line texture */
body::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: repeating-linear-gradient(
    0deg, rgba(255,255,255,0.012) 0 1px, transparent 1px 3px
  );
  mix-blend-mode: overlay;
}
```

---

## Layout

| Surface | Max-width | Padding |
|---------|-----------|----------|
| Marketing / widget demo | 980px | 32px |
| Merchant dashboard | 1400px | 28px 32px |

| Grid | Columns | Gap |
|------|---------|-----|
| Stat row | `repeat(5, 1fr)` | 12px |
| Feature cards | `repeat(3, 1fr)` | 16px |
| Product section | `1.1fr 1fr` | 40px |

---

## Design Principles

1. **No color on white.** All surfaces are dark. Text glows against the void.
2. **Data first.** Every element either shows a number or labels one.
3. **Two accent colors only.** Orange is action. Gold is premium/status.
4. **Monospace for money.** All financial figures use JetBrains Mono.
5. **Borders, not shadows.** Elevation via border color, not `box-shadow` (except primary CTA).
6. **ALL CAPS for labels.** Secondary text is always uppercase with letter-spacing.

---

## Stitch Project

**Project ID:** `294283250106200241`  
**URL:** `https://stitch.withgoogle.com/projects/294283250106200241`

To pull screens into your editor, use the `stitch` MCP tool configured in `.claude/settings.json`.  
To export a screen as HTML/CSS: open the screen in Stitch → **Export to code**.
