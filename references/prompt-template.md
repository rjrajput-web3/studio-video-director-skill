# Six-Part Video Prompt Template

One prompt per segment. Each segment is **<= 10 seconds** and holds
**2-3 shots maximum**. Write the timeline in 10-second chunks, never a
15/30-second axis (generators compress long axes and drop beats).

**Discipline that prevents face/wardrobe drift:** the subject
description is copied **verbatim** into every segment of the same
video. Rewriting it is the #1 cause of a changed face. The
constraints list is deliberately long -- every failure you have ever
seen (warping, morphing, over-smoothing, wrong framing) goes in
explicitly.

## The six parts

```
[Duration / format] [one-sentence scene]
Subject: age / gender / appearance / clothing / hairstyle (exact colors and cuts)
Scene: location / time of day / light / mood
Beats (with timestamps):
  0-2s: ...
  2-5s: ...
  5-8s: ...
Camera: position / movement / shot size / handheld or stabilized / forbidden moves
Sound: ambience / foley / dialogue (mark which lines are spoken)
Dialogue language: (state it; delete this line if there is no dialogue)
Reference image note: (which part of the reference to use -- face, outfit, or set only; ASCII filenames)
Constraints: never ... (one per line: warping, morphing, skin smoothing, ... )
```

## Vertical template (9:16 Shorts / Reels)

```
[8 seconds, 9:16 vertical, 1080x1920, 30fps] A street-food vendor flips
a sizzling dosa as a crowd gathers at dusk.
Subject: Male vendor, ~45, weathered hands, white kurta with rolled sleeves,
  navy apron, short grey-flecked hair, focused expression.
Scene: Busy night-market stall, warm tungsten bulbs, steam rising, shallow
  depth of field, crowd bokeh behind.
Beats (with timestamps):
  0-2s: HOOK -- extreme close-up, batter hisses as it hits the hot griddle.
  2-5s: Medium shot, vendor flips the dosa in one confident motion.
  5-8s: Slow push-in on the finished dosa, steam curls, vendor smiles briefly.
Camera: Handheld with subtle float, 35mm feel, no drone shots, no whip pans.
Sound: Sizzle, distant market chatter, one vendor line: "Fresh off the griddle!"
Dialogue language: English with a light Indian accent.
Constraints: never warp hands or fingers; never morph the face between shots;
  never smooth skin; never add text overlays; never change the apron color.
```

## Landscape template (16:9 demos / long-form)

```
[10 seconds, 16:9 landscape, 1920x1080, 30fps] A founder demos a real-time
analytics dashboard on a laptop in a bright office.
Subject: Female founder, ~30, dark blazer, hair tied back, confident and calm.
Scene: Modern office desk, soft daylight from the left, laptop screen facing
  camera, clean background, no clutter.
Beats (with timestamps):
  0-3s: HOOK -- over-shoulder shot, dashboard loads, a revenue chart spikes.
  3-7s: Cut to front three-quarter shot, founder clicks "Live view", numbers tick up.
  7-10s: Close-up of the chart, then a slow pull-back revealing the full desk.
Camera: Locked-off tripod for the screen shots, slow dolly for the pull-back,
  no shaky cam, no Dutch angles.
Sound: Soft keyboard clicks, quiet room tone, founder line: "Watch it update live."
Dialogue language: English, neutral accent.
Constraints: never show unreadable or gibberish UI text; never warp the laptop
  screen; never add fake logos; never cut to a different room.
```

## Multi-segment continuity (videos > 10 s)

Start every segment after the first with this line, verbatim:

> This is segment N of a [30]-second video (seconds [X-Y]), continuing
> the same subject / scene / light / texture as the previous segment.
> Subject appearance, clothing, hairstyle and face stay strictly identical.

Then write only this segment's 2-3 shots. Never re-describe the whole
video in a later segment.

## Variants

- **POV / lifestyle:** open with `Strict first-person throughout: the
  camera IS the viewer's eyes. The subject never appears on camera;
  only hands or forearms may enter the frame edge.`
- **Talking head:** subject faces camera, eyeline into the lens;
  state `not a selfie -- no camera or phone visible in frame`; put
  dialogue in quotes with tone and lip-sync notes.
- **Screen-recording demo (16:9):** this template is NOT for screen
  capture. Demos are real Playwright recordings (deviceScaleFactor 2),
  not generated video. Use the prompt template only for B-roll,
  openers, and end cards around the real recording.
