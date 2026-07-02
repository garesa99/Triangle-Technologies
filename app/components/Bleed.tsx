'use client';

import { useState } from 'react';

type Props = {
  src: string;
  alt: string;
  overlay?: 'bottom' | 'side' | 'none';
  className?: string;
  style?: React.CSSProperties;
};

/**
 * Full-bleed image with a dark solid block behind it so it degrades
 * gracefully when the (external) image fails to load or is unreachable.
 * Core layout never depends on the runtime fetch succeeding.
 */
export default function Bleed({
  src,
  alt,
  overlay = 'bottom',
  className = '',
  style,
}: Props) {
  const [failed, setFailed] = useState(false);

  return (
    <div className={`bleed ${className}`} style={style}>
      <div className="img-fallback" aria-hidden={failed ? undefined : true} />
      {!failed && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      )}
      {overlay === 'bottom' && <div className="overlay" />}
      {overlay === 'side' && <div className="overlay-side" />}
    </div>
  );
}
