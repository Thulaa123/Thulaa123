# Character animation

The character comes from Thulana's supplied video. Its background was removed frame by frame with local Apple Vision foreground segmentation; the matte edges were refined and the empty canvas cropped. No replacement character was generated. Audio is intentionally omitted.

- `thulana-wave.gif`: transparent, looping README animation; 348 × 420 pixels, 120 frames, approximately 10 seconds.
- `thulana-still.png`: transparent still used when the browser requests reduced motion.
- `thulana-wave.lottie.json`: self-contained Lottie image sequence; 224 × 270 pixels, 120 frames at 12 fps, with embedded transparent PNGs. This preserves the original 3D appearance. It is a raster-backed Lottie, not an editable vector rig.
- `header.svg`: scalable profile banner.

GitHub READMEs cannot run a JavaScript Lottie player. The README embeds the GIF; the Lottie asset can be reused on a website with an image-layer-compatible player such as lottie-web.

The Holopin board remains linked to the original live profile.
