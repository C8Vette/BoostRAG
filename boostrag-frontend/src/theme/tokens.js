// Two-zone design tokens — "showroom upstairs, garage downstairs".
export const tokens = {
  color: {
    // neutral scale
    white: "#FFFFFF", gallery: "#F6F6F4", fog: "#E8E8E6", steel: "#9CA3AF",
    graphite: "#27272A", tar: "#111113", black: "#0A0A0B",
    // M accents — jewelry, never flood (≤5% of any viewport)
    mBlue: "#0066B1", mRed: "#E7222E", streetYellow: "#FACC15",
  },
  font: {
    heading: "'Archivo', 'Inter', system-ui, sans-serif", // precise grotesk voice
    body: "'Inter', system-ui, sans-serif",
  },
  space: (n) => `${n * 8}px`, // 8px grid; showroom uses generous multipliers
  motion: {
    swellScale: 1.04, swellMs: 150, revealMs: 250, revealRise: 12, kenburnsS: 26,
  },
};
