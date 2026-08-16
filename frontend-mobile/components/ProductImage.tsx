"use client";

import { useState } from "react";
import { imageProxyUrl } from "@/lib/format";

export function ProductImage({
  articleId,
  alt,
  className = "",
}: {
  articleId: string;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        className={`flex items-center justify-center bg-neutral-100 text-xs text-hm-muted ${className}`}
      >
        No image
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={imageProxyUrl(articleId)}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`object-cover ${className}`}
    />
  );
}
