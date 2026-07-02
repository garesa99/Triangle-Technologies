import type { Metadata } from "next";
import "maplibre-gl/dist/maplibre-gl.css";
import "../console.css";

export const metadata: Metadata = {
  title: "Triangle Mesh — Operator Console",
  robots: { index: false, follow: false },
};

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="console-shell">
      <a className="console-back" href="/">
        &larr; Back to site
      </a>
      {children}
    </div>
  );
}
