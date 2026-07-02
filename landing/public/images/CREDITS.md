# Image credits & licensing

All photographic imagery on the Triangle Mesh landing page is sourced from
**Unsplash** under the [Unsplash License](https://unsplash.com/license).

The Unsplash License grants free use for commercial and non-commercial
purposes with **no permission or attribution required**. Attribution is
appreciated but not legally mandated. (You may not sell unmodified copies of
the photos, nor use them to build a competing image-licensing service — neither
applies here.)

## Runtime independence

The site does **not** depend on a runtime internet fetch for its core layout.
Every photo is rendered through the `Bleed` component, which paints a dark
solid block (`.img-fallback`) behind the image and swaps to that block on any
load error (`onError`). If an image is unreachable, the layout is unaffected
and the section simply shows the dark backdrop. A unified dark duotone /
desaturation CSS filter is applied to all photos so the set reads cohesively.

## Images used (direct Unsplash hotlinks)

| Slot    | Theme                                  | Unsplash photo ID (URL)                                                            | Source   | License          |
| ------- | -------------------------------------- | --------------------------------------------------------------------------------- | -------- | ---------------- |
| hero    | Drone silhouette against sky           | https://images.unsplash.com/photo-1473968512647-3e447244af8f                      | Unsplash | Unsplash License |
| terrain | Field terrain / night-vision mood      | https://images.unsplash.com/photo-1441974231531-c6227db76b6e                      | Unsplash | Unsplash License |
| tower   | Radio / transmission tower             | https://images.unsplash.com/photo-1518623489648-a173ef7824f3                      | Unsplash | Unsplash License |
| circuit | Circuit board (node hardware)          | https://images.unsplash.com/photo-1518770660439-4636190af475                      | Unsplash | Unsplash License |
| dusk    | Field terrain at dusk                  | https://images.unsplash.com/photo-1500534623283-312aade485b7                      | Unsplash | Unsplash License |

> Photo IDs above were selected to match the stated themes (drone/sky,
> thermal-mood landscape, radio tower, circuit board, field at dusk). Before
> public launch, open each Unsplash page (`https://unsplash.com/photos/<id>`)
> to visually confirm the exact frame and that it still carries the Unsplash
> License, then replace any that no longer fit. Because the layout degrades
> gracefully, a bad hotlink never breaks the page — it only shows the dark
> backdrop.

## Original diagrams (ours)

The three technical SVG diagrams (triangulation geometry, sensor-layer stack,
mesh relay topology) are **original work created for Triangle Mesh**. They are
not stock and not product screenshots. They are labeled "Illustrative" in the
UI. No third-party license applies.
