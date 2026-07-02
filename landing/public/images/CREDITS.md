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
and the section simply shows the dark backdrop. A unified **pure black & white**
CSS filter (`grayscale(1)`, higher contrast) is applied to every photo, so the
set reads as stark monochrome silhouettes.

## Images used (direct Unsplash hotlinks)

Currently referenced by the page: **hero** and **circuit** only.

| Slot    | Theme                                  | Unsplash photo ID (URL)                                                            | Source   | License          | In use |
| ------- | -------------------------------------- | --------------------------------------------------------------------------------- | -------- | ---------------- | ------ |
| hero    | Uncrewed aircraft, silhouette vs sky   | https://images.unsplash.com/photo-1569228593208-6314ad85a2ba                      | Unsplash | Unsplash License | yes    |
| circuit | Circuit board (node hardware)          | https://images.unsplash.com/photo-1518770660439-4636190af475                      | Unsplash | Unsplash License | yes    |

Hero note: free-license military/fixed-wing UAV photos on Unsplash are almost
all **Unsplash+ (paid)**. To stay license-clean we use a free, unbranded drone
shown in **silhouette against sky** — which also reads on-thesis (an *unknown /
uncooperative* aircraft). If you want a paid Unsplash+ military-UAV frame
instead, that's a licensing decision to make before launch.

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
