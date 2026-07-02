"use client";

import dynamic from "next/dynamic";

// MapLibre needs the DOM — render the console client-only (no SSR).
const Console = dynamic(() => import("../../components/Console"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#7C7C85",
        fontFamily: 'ui-monospace, "JetBrains Mono", "SFMono-Regular", Menlo, monospace',
        letterSpacing: "0.1em",
      }}
    >
      TRIANGLE MESH — INITIALIZING OPERATOR PICTURE…
    </div>
  ),
});

export default function ConsolePage() {
  return <Console />;
}
