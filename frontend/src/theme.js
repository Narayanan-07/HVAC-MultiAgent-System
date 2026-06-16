// "Neon noir" palette · shared across the app UI.
// #2CFF05 neon green (primary) · #BF00FF neon purple (secondary)
// #2D2D2D dark grey (surfaces/borders) · #000000 black (background)
export const T = {
  bg:        '#000000',
  surface:   '#0c0c0c',
  surface2:  '#161616',
  surface3:  '#2D2D2D',
  border:    '#2D2D2D',
  borderHi:  'rgba(44,255,5,0.4)',   // neon-green glow
  text:      '#f7f7f5',
  soft:      '#b0b0b0',
  muted:     '#7a7a7a',
  kiwi:      '#2CFF05',   // primary accent (neon green)
  kiwi2:     '#BF00FF',   // secondary accent (neon purple)
  yellow:    '#2CFF05',   // tertiary accent — kept green so cards alternate green/purple/green
  red:       '#ff5d5d',
};

export const card = {
  background: T.surface,
  border: `1px solid ${T.border}`,
  borderRadius: 14,
};

export const input = {
  background: T.surface2,
  border: `1px solid ${T.border}`,
  borderRadius: 10,
  color: T.text,
  outline: 'none',
  width: '100%',
  padding: '11px 14px',
  fontSize: 13,
  transition: 'border-color .15s, box-shadow .15s',
};

// Primary call to action: neon green fill, black text for maximum contrast.
export const cta = {
  background: T.kiwi,
  color: '#000000',
  border: 'none',
  borderRadius: 12,
  cursor: 'pointer',
  fontWeight: 700,
  transition: 'transform .12s, box-shadow .2s, background .2s',
  boxShadow: '0 6px 24px rgba(44,255,5,0.22)',
};
