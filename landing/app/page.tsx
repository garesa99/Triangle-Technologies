import Nav from './components/Nav';
import Reveal from './components/Reveal';
import Bleed from './components/Bleed';
import {
  TriangulationDiagram,
  SensorStackDiagram,
  MeshDiagram,
} from './components/Diagrams';

/* Direct Unsplash hotlinks — Unsplash License (free commercial use, no
   attribution required). Cataloged in public/images/CREDITS.md.
   Images degrade to a dark solid block via <Bleed>. */
const IMG = {
  hero:
    'https://images.unsplash.com/photo-1569228593208-6314ad85a2ba?auto=format&fit=crop&w=2000&q=70',
  circuit:
    'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=70',
};

/* Live operator console. Set NEXT_PUBLIC_DEMO_URL to the deployed (passcode-protected,
   noindex) console for production; defaults to a local instance for review. */
const DEMO_URL = process.env.NEXT_PUBLIC_DEMO_URL || 'http://localhost:3000';

export default function Home() {
  return (
    <>
      <Nav />
      <main id="top">
        {/* ---------------- HERO ---------------- */}
        <section className="hero">
          <div className="hero-media">
            <Bleed src={IMG.hero} alt="An uncrewed aircraft in silhouette against an open sky" className="" style={{ position: 'absolute', inset: 0 }} />
          </div>
          <div className="hero-grid-lines" aria-hidden="true" />
          <div className="hero-content">
            <Reveal>
              <span className="eyebrow">Passive · Distributed · Attritable</span>
            </Reveal>
            <Reveal delay={100}>
              <h1 className="display" style={{ marginTop: 28, maxWidth: '16ch' }}>
                Detect drones that don&rsquo;t want to be seen.
              </h1>
            </Reveal>
            <Reveal delay={200}>
              <p className="lead" style={{ marginTop: 28 }}>
                A mesh of passive sensors, built from commercially available
                components, that hears drones, fuses the contacts, and
                triangulates them.
              </p>
            </Reveal>
            <Reveal delay={300}>
              <div style={{ marginTop: 44, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <a href="#contact" className="btn">
                  Request a briefing <span className="arrow">&rarr;</span>
                </a>
                <a href={DEMO_URL} target="_blank" rel="noopener noreferrer" className="btn btn-ghost">
                  Open the live console <span className="arrow">&rarr;</span>
                </a>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ---------------- THE PROBLEM ---------------- */}
        <section id="problem" className="section-pad">
          <div className="wrap">
            <div className="sec-head">
              <Reveal>
                <span className="eyebrow">01 — The problem</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="h2" style={{ marginTop: 20 }}>
                  Today&rsquo;s systems only see the aircraft that announce
                  themselves.
                </h2>
              </Reveal>
              <Reveal delay={140}>
                <p className="body lead" style={{ maxWidth: '54ch' }}>
                  Remote ID and ADS-B assume a compliant operator. The threat
                  broadcasts nothing. That is the gap.
                </p>
              </Reveal>
            </div>

            <Reveal>
              <div className="stat-grid">
                <div className="stat">
                  <div className="stat-num">
                    Cost <span className="accent">asymmetry</span>
                  </div>
                  <div className="stat-label">
                    A drone can cost a few hundred euros. The interceptors used
                    against them can cost far more per shot.
                  </div>
                  <div className="stat-src">
                    Qualitative — figures vary by system.
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-num">
                    Airport <span className="accent">incursions</span>
                  </div>
                  <div className="stat-label">
                    Drone sightings closed London Gatwick for ~33 hours in
                    December 2018, affecting ~140,000 passengers.
                  </div>
                  <div className="stat-src">
                    Source:{' '}
                    <a
                      href="https://en.wikipedia.org/wiki/Gatwick_Airport_drone_incident"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Gatwick drone incident (public record)
                    </a>
                  </div>
                </div>
                <div className="stat">
                  <div className="stat-num">
                    Rising <span className="accent">exposure</span>
                  </div>
                  <div className="stat-label">
                    Incidents near airports, borders, and critical sites keep
                    rising — while the barrier to entry stays low.
                  </div>
                  <div className="stat-src">
                    Qualitative. We avoid inventing precise counts.
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        <div className="wrap">
          <hr className="hairline" />
        </div>

        {/* ---------------- HOW IT WORKS ---------------- */}
        <section id="how" className="section-pad">
          <div className="wrap">
            <div className="sec-head">
              <Reveal>
                <span className="eyebrow">02 — How it works</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="h2" style={{ marginTop: 20 }}>
                  Listen. Fuse. Locate.
                </h2>
              </Reveal>
            </div>

            <div className="steps">
              <Reveal className="step">
                <span className="step-index">LISTEN</span>
                <h3>Signatures it cannot hide</h3>
                <p className="body">
                  Each node passively picks up rotor acoustics and control /
                  video RF. A quiet drone still moves air and still talks to its
                  pilot.
                </p>
              </Reveal>
              <Reveal className="step" delay={100}>
                <span className="step-index">FUSE</span>
                <h3>Cross-cue and friend-or-foe</h3>
                <p className="body">
                  Contacts combine across the mesh. A cooperative drone
                  broadcasts Remote ID — its <em>absence</em> around a track is
                  itself a signal.
                </p>
              </Reveal>
              <Reveal className="step" delay={200}>
                <span className="step-index">LOCATE</span>
                <h3>Triangulate, honestly</h3>
                <p className="body">
                  Enough bearings give a fix with an explicit uncertainty
                  ellipse. Fewer nodes, coarser fix — and the system says so.
                </p>
              </Reveal>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: 24,
                marginTop: 64,
              }}
            >
              <Reveal className="diagram">
                <span className="illus-tag">Illustrative</span>
                <TriangulationDiagram />
                <div className="diagram-cap">
                  Fig. 01 — Bearing triangulation &amp; uncertainty ellipse
                </div>
              </Reveal>
              <Reveal className="diagram" delay={100}>
                <span className="illus-tag">Illustrative</span>
                <SensorStackDiagram />
                <div className="diagram-cap">Fig. 02 — Passive sensor layers</div>
              </Reveal>
              <Reveal className="diagram" delay={200}>
                <span className="illus-tag">Illustrative</span>
                <MeshDiagram />
                <div className="diagram-cap">Fig. 03 — Mesh relay topology</div>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ---------------- THE NODE ---------------- */}
        <section id="node" className="section-pad" style={{ background: '#08080a' }}>
          <div className="wrap">
            <div className="sec-head">
              <Reveal>
                <span className="eyebrow">03 — The node</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="h2" style={{ marginTop: 20 }}>
                  Commodity parts. Emits nothing.
                </h2>
              </Reveal>
              <Reveal delay={140}>
                <p className="body lead" style={{ maxWidth: '54ch' }}>
                  Built entirely from commercially available components —
                  affordable to field at scale, and attritable by design. Purely
                  passive: it listens, never transmits.
                </p>
              </Reveal>
            </div>

            <div className="node-grid">
              <Reveal>
                <table className="spec-table">
                  <tbody>
                    <tr>
                      <td>Compute</td>
                      <td>Quad-core ARM64 single-board computer (Linux)</td>
                    </tr>
                    <tr>
                      <td>Acoustic</td>
                      <td>USB / I2S MEMS microphone array</td>
                    </tr>
                    <tr>
                      <td>RF</td>
                      <td>SDR receiver — 2.4 &amp; 5.8 GHz survey</td>
                    </tr>
                    <tr>
                      <td>Remote-ID</td>
                      <td>ESP32 OpenDroneID receiver</td>
                    </tr>
                    <tr>
                      <td>Timing / Pos</td>
                      <td>u-blox GNSS (time + node fix)</td>
                    </tr>
                    <tr>
                      <td>Emission</td>
                      <td>None — receive-only, no active radar</td>
                    </tr>
                    <tr>
                      <td>BOM target</td>
                      <td>~ &euro;150 per node</td>
                    </tr>
                    <tr>
                      <td>Power</td>
                      <td>Battery / solar-capable, low draw</td>
                    </tr>
                  </tbody>
                </table>
                <div className="spec-badges">
                  <span className="badge hi">Passive</span>
                  <span className="badge hi">Attritable</span>
                  <span className="badge">Commodity HW</span>
                  <span className="badge">Field-serviceable</span>
                  <span className="badge">Open schema</span>
                </div>
              </Reveal>

              <Reveal delay={120}>
                <Bleed
                  src={IMG.circuit}
                  alt="Close-up of a circuit board, representing commodity node hardware"
                  overlay="side"
                  style={{ aspectRatio: '4 / 5', minHeight: 320 }}
                />
              </Reveal>
            </div>
          </div>
        </section>

        {/* ---------------- THE MESH ---------------- */}
        <section id="mesh" className="section-pad">
          <div className="wrap">
            <div className="two-col reverse">
              <Reveal className="col-media">
                <div className="diagram" style={{ background: 'var(--bg)' }}>
                  <span className="illus-tag">Illustrative</span>
                  <MeshDiagram />
                  <div className="diagram-cap">
                    Losing a node degrades resolution — it never blinds the mesh
                  </div>
                </div>
              </Reveal>
              <Reveal delay={100}>
                <span className="eyebrow">04 — The mesh</span>
                <h2 className="h2" style={{ marginTop: 20 }}>
                  Scales with nodes. Fails gracefully.
                </h2>
                <ul className="flist">
                  <li>
                    <span className="mark">/ /</span>
                    <span>
                      <strong>Coverage scales linearly.</strong> More nodes, more
                      overlap, tighter fixes.
                    </span>
                  </li>
                  <li>
                    <span className="mark">/ /</span>
                    <span>
                      <strong>Nodes cue each other.</strong> A weak hit becomes a
                      confident track when neighbors agree.
                    </span>
                  </li>
                  <li>
                    <span className="mark">/ /</span>
                    <span>
                      <strong>No single point of blindness.</strong> Lose a node
                      and the mesh reroutes — resolution drops, awareness does
                      not.
                    </span>
                  </li>
                </ul>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ---------------- HONEST CAPABILITY ---------------- */}
        <section
          id="honest"
          className="section-pad"
          style={{ borderTop: '1px solid var(--hairline)', borderBottom: '1px solid var(--hairline)' }}
        >
          <div className="wrap">
            <div className="two-col">
              <Reveal>
                <span className="eyebrow">05 — Honest capability</span>
                <h2 className="h2" style={{ marginTop: 20, maxWidth: '14ch' }}>
                  Systems that overclaim get people hurt.
                </h2>
              </Reveal>
              <Reveal delay={120}>
                <p className="body lead" style={{ maxWidth: '52ch' }}>
                  Detection is probabilistic and bounded by physics. We treat
                  that as engineering, not marketing.
                </p>
                <ul className="flist">
                  <li>
                    <span className="mark">01</span>
                    <span>
                      <strong>Every track carries a confidence.</strong>
                    </span>
                  </li>
                  <li>
                    <span className="mark">02</span>
                    <span>
                      <strong>Uncertainty is shown, never hidden.</strong>
                    </span>
                  </li>
                  <li>
                    <span className="mark">03</span>
                    <span>
                      <strong>We state where the sensing ends.</strong>
                    </span>
                  </li>
                </ul>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ---------------- ROADMAP ---------------- */}
        <section id="roadmap" className="section-pad">
          <div className="wrap">
            <div className="sec-head">
              <Reveal>
                <span className="eyebrow">06 — Roadmap &amp; extensibility</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="h2" style={{ marginTop: 20 }}>
                  New sensors plug into one shared schema.
                </h2>
              </Reveal>
              <Reveal delay={140}>
                <p className="body lead" style={{ maxWidth: '54ch' }}>
                  Each future layer publishes to the same fusion schema the
                  acoustic and RF layers already use.
                </p>
              </Reveal>
            </div>

            <Reveal>
              <div className="road-grid">
                <div className="road">
                  <span className="mono-tag">Layer · Seismic</span>
                  <h3>Ground vibration</h3>
                  <p>Geophone sensing for low, close passes.</p>
                </div>
                <div className="road">
                  <span className="mono-tag">Layer · Magnetometer</span>
                  <h3>Magnetic anomaly</h3>
                  <p>Motor and battery signatures as a corroborating cue.</p>
                </div>
                <div className="road">
                  <span className="mono-tag">Layer · PIR</span>
                  <h3>Passive infrared</h3>
                  <p>Low-power thermal triggers that wake the richer sensors.</p>
                </div>
                <div className="road">
                  <span className="mono-tag">Layer · Camera</span>
                  <h3>Visual cueing</h3>
                  <p>Slew-to-cue optical confirmation on an existing track.</p>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ---------------- CONTACT / FOOTER ---------------- */}
        <section id="contact" className="contact">
          <div className="wrap">
            <div className="contact-inner">
              <Reveal>
                <span className="eyebrow">07 — Contact</span>
                <h2 className="h2" style={{ marginTop: 20, maxWidth: '18ch' }}>
                  Talk to us about the uncooperative airspace.
                </h2>
                <p className="body lead" style={{ maxWidth: '48ch', marginTop: 20 }}>
                  Built for the NATO DIANA application. For a briefing or
                  evaluation, get in touch.
                </p>
                <p className="disclaimer">
                  Triangle Mesh is an independent effort. This page uses no NATO
                  or DIANA marks and implies no endorsement, affiliation, or
                  selection. All diagrams are our own technical illustrations,
                  not live-detection screenshots.
                </p>
              </Reveal>
              <Reveal delay={120}>
                <div>
                  <a
                    className="btn"
                    href="mailto:contact@triangletechno.com?subject=Triangle%20Mesh%20—%20Briefing%20request&body=Hi%20Triangle%20Mesh%20team%2C%0A%0AI%27d%20like%20to%20learn%20more%20about%20the%20passive%20drone-detection%20mesh.%0A%0A"
                  >
                    Email the team <span className="arrow">&rarr;</span>
                  </a>
                  <p
                    className="mono"
                    style={{ marginTop: 20, fontSize: '0.78rem', color: 'var(--fg-faint)' }}
                  >
                    contact@triangletechno.com
                  </p>
                  <p style={{ marginTop: 24 }}>
                    <a
                      href={DEMO_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mono"
                      style={{ fontSize: '0.78rem', color: 'var(--fg)', borderBottom: '1px solid var(--hairline-strong)', paddingBottom: 2 }}
                    >
                      → Open the live operator console
                    </a>
                  </p>
                </div>
              </Reveal>
            </div>

            <div className="footer-bar">
              <span>TRIANGLE MESH · PASSIVE DRONE-DETECTION MESH</span>
              <span>NOINDEX · PRE-LAUNCH · {new Date().getFullYear()}</span>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
