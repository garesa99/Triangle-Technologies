const DEMO_URL = process.env.NEXT_PUBLIC_DEMO_URL || '/console';

export default function Nav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <a href="#top" className="nav-brand" aria-label="Triangle Mesh — home">
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <polygon
              points="9,2 16,15 2,15"
              fill="none"
              stroke="#f4f4f5"
              strokeWidth="1.3"
            />
            <circle cx="9" cy="2" r="1.4" fill="#f4f4f5" />
            <circle cx="16" cy="15" r="1.4" fill="#f4f4f5" />
            <circle cx="2" cy="15" r="1.4" fill="#f4f4f5" />
          </svg>
          <span>TRIANGLE&nbsp;MESH</span>
        </a>
        <div className="nav-links">
          <a href="#problem">Problem</a>
          <a href="#how">How it works</a>
          <a href="#node">The node</a>
          <a href="#mesh">The mesh</a>
          <a href="#honest">Capability</a>
          <a href={DEMO_URL}>Live demo</a>
          <a href="#contact" className="nav-cta">
            Contact
          </a>
        </div>
      </div>
    </nav>
  );
}
