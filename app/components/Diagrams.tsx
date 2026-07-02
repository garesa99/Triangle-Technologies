/* Original technical diagrams — pure black & white. The "highlight" is bright
   white against dim grey strokes. These are OURS. Not product screenshots. */

const STROKE = '#3f3f46';
const STROKE_HI = '#f4f4f5';
const ACCENT = '#f4f4f5';
const LABEL = '#a1a1aa';
const FAINT = '#71717a';

const mono = {
  fontFamily: 'var(--font-mono), monospace',
  fontSize: 10,
  letterSpacing: '0.08em',
  textTransform: 'uppercase' as const,
};

/* 1. Triangulation geometry — three nodes, bearing rays, intersection ellipse */
export function TriangulationDiagram() {
  return (
    <svg viewBox="0 0 420 300" role="img" aria-label="Triangulation geometry: three sensor nodes cast bearing rays that intersect at an uncertainty ellipse.">
      {/* target uncertainty ellipse */}
      <ellipse
        cx="210"
        cy="150"
        rx="34"
        ry="20"
        fill="rgba(244,244,245,0.14)"
        stroke={ACCENT}
        strokeWidth="1"
        strokeDasharray="3 3"
      />
      <circle cx="210" cy="150" r="3" fill={ACCENT} />

      {/* node A */}
      <g>
        <line x1="60" y1="60" x2="210" y2="150" stroke={STROKE} strokeWidth="1" />
        <line x1="60" y1="60" x2="228" y2="132" stroke={STROKE} strokeWidth="1" strokeDasharray="2 4" opacity="0.5" />
        <rect x="52" y="52" width="16" height="16" fill="#0a0a0b" stroke={STROKE_HI} strokeWidth="1.2" />
        <circle cx="60" cy="60" r="2" fill={ACCENT} />
        <text x="46" y="44" style={mono} fill={LABEL}>NODE A</text>
      </g>

      {/* node B */}
      <g>
        <line x1="360" y1="70" x2="210" y2="150" stroke={STROKE} strokeWidth="1" />
        <line x1="360" y1="70" x2="192" y2="132" stroke={STROKE} strokeWidth="1" strokeDasharray="2 4" opacity="0.5" />
        <rect x="352" y="62" width="16" height="16" fill="#0a0a0b" stroke={STROKE_HI} strokeWidth="1.2" />
        <circle cx="360" cy="70" r="2" fill={ACCENT} />
        <text x="330" y="54" style={mono} fill={LABEL}>NODE B</text>
      </g>

      {/* node C */}
      <g>
        <line x1="150" y1="250" x2="210" y2="150" stroke={STROKE} strokeWidth="1" />
        <line x1="150" y1="250" x2="228" y2="164" stroke={STROKE} strokeWidth="1" strokeDasharray="2 4" opacity="0.5" />
        <rect x="142" y="242" width="16" height="16" fill="#0a0a0b" stroke={STROKE_HI} strokeWidth="1.2" />
        <circle cx="150" cy="250" r="2" fill={ACCENT} />
        <text x="120" y="278" style={mono} fill={LABEL}>NODE C</text>
      </g>

      <text x="248" y="154" style={mono} fill={ACCENT}>FIX ± σ</text>
    </svg>
  );
}

/* 2. Sensor-layer stack */
export function SensorStackDiagram() {
  const layers = [
    { t: 'ACOUSTIC', s: 'Rotor / motor harmonics', y: 40 },
    { t: 'RF 2.4 / 5.8 GHz', s: 'Control + video downlink', y: 90 },
    { t: 'REMOTE-ID', s: 'Broadcast presence / absence', y: 140 },
    { t: 'GNSS', s: 'Node time + position reference', y: 190 },
  ];
  return (
    <svg viewBox="0 0 420 260" role="img" aria-label="Sensor layer stack: acoustic, RF 2.4 to 5.8 gigahertz, Remote-ID, and GNSS layers feeding a fusion bus.">
      {layers.map((l, i) => (
        <g key={l.t}>
          <rect
            x="20"
            y={l.y}
            width="300"
            height="38"
            fill={i === 2 ? 'rgba(244,244,245,0.10)' : '#101012'}
            stroke={i === 2 ? ACCENT : STROKE}
            strokeWidth="1"
          />
          <text x="34" y={l.y + 17} style={{ ...mono, fontSize: 11 }} fill={i === 2 ? ACCENT : STROKE_HI}>
            {l.t}
          </text>
          <text x="34" y={l.y + 30} style={{ ...mono, fontSize: 8, textTransform: 'none' }} fill={FAINT}>
            {l.s}
          </text>
          {/* connector to fusion bus */}
          <line x1="320" y1={l.y + 19} x2="360" y2="128" stroke={STROKE} strokeWidth="1" opacity="0.6" />
        </g>
      ))}
      {/* fusion bus */}
      <rect x="360" y="112" width="44" height="34" fill="#0a0a0b" stroke={ACCENT} strokeWidth="1.2" />
      <text x="382" y="132" style={{ ...mono, fontSize: 8 }} fill={ACCENT} textAnchor="middle">FUSE</text>
    </svg>
  );
}

/* 3. Mesh relay topology — nodes, links, one relay path highlighted, one brain */
export function MeshDiagram() {
  const nodes = [
    { id: 'n1', x: 60, y: 70 },
    { id: 'n2', x: 160, y: 40 },
    { id: 'n3', x: 150, y: 150 },
    { id: 'n4', x: 260, y: 100 },
    { id: 'n5', x: 70, y: 190 },
    { id: 'n6', x: 250, y: 210 },
  ];
  const brain = { x: 370, y: 130 };
  const links: [string, string][] = [
    ['n1', 'n2'],
    ['n1', 'n3'],
    ['n2', 'n4'],
    ['n3', 'n4'],
    ['n3', 'n5'],
    ['n4', 'n6'],
    ['n5', 'n6'],
  ];
  // highlighted relay path: n5 -> n3 -> n4 -> brain
  const relay = new Set(['n5-n3', 'n3-n4']);
  const N = (id: string) => nodes.find((n) => n.id === id)!;

  return (
    <svg viewBox="0 0 430 260" role="img" aria-label="Mesh relay topology: distributed nodes linked peer-to-peer, one relay path highlighted forwarding to a central fusion brain.">
      {links.map(([a, b]) => {
        const A = N(a);
        const B = N(b);
        const hi = relay.has(`${a}-${b}`) || relay.has(`${b}-${a}`);
        return (
          <line
            key={`${a}-${b}`}
            x1={A.x}
            y1={A.y}
            x2={B.x}
            y2={B.y}
            stroke={hi ? ACCENT : STROKE}
            strokeWidth={hi ? 1.5 : 1}
            strokeDasharray={hi ? undefined : '3 3'}
          />
        );
      })}
      {/* relay leg into brain */}
      <line x1={N('n4').x} y1={N('n4').y} x2={brain.x} y2={brain.y} stroke={ACCENT} strokeWidth="1.5" />

      {nodes.map((n) => {
        const onPath = ['n5', 'n3', 'n4'].includes(n.id);
        return (
          <g key={n.id}>
            <rect
              x={n.x - 7}
              y={n.y - 7}
              width="14"
              height="14"
              fill="#0a0a0b"
              stroke={onPath ? ACCENT : STROKE_HI}
              strokeWidth="1.2"
            />
            <circle cx={n.x} cy={n.y} r="2" fill={onPath ? ACCENT : LABEL} />
          </g>
        );
      })}

      {/* brain */}
      <circle cx={brain.x} cy={brain.y} r="16" fill="rgba(244,244,245,0.10)" stroke={ACCENT} strokeWidth="1.2" />
      <circle cx={brain.x} cy={brain.y} r="4" fill={ACCENT} />
      <text x={brain.x} y={brain.y + 34} style={{ ...mono, fontSize: 9 }} fill={ACCENT} textAnchor="middle">BRAIN</text>
      <text x="52" y="24" style={{ ...mono, fontSize: 9 }} fill={FAINT}>MESH · P2P</text>
    </svg>
  );
}
