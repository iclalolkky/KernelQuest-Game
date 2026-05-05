# Audio stems — Phase 8

Kernel Quest uses an adaptive stem-based music director (`ui/music.py`).
Each stem is a short loop authored to layer cleanly on top of the others.

## Stem inventory

| Stem key       | Role                                | Trigger archetype(s)            |
| -------------- | ----------------------------------- | ------------------------------- |
| `bed`          | Always on; sets sector tonality     | (always)                        |
| `melody_lead`  | Calm pursuit theme                  | Skirmisher                      |
| `melody_arp`   | Caster stutter motif                | Caster                          |
| `melody_pad`   | Support drone                       | Support                         |
| `tension_lead` | Rising lead — danger up close       | Sapper                          |
| `tension_low`  | Sub-bass drone — heavies on screen  | Bruiser, Revenant               |
| `tension_pad`  | Whisper pad — stalker proximity     | Stalker                         |
| `boss`         | Boss override loop                  | Boss (`is_boss=True`)           |

## Authoring rules

- **Tempo / key.** All stems must share the same BPM and root key per
  sector. Sector palette → key map lives in `data/sector_palette.py`
  (TBD); for v1 use 100 BPM C-minor everywhere.
- **Length.** 4 or 8 bars; loop seamlessly with no fade-in/out built into
  the file (the mixer crossfades).
- **Headroom.** Master each stem to **−6 dBFS RMS** so layered combinations
  stay below 0 dBFS without dynamic processing.
- **No solo cues.** Stems must read as ambience, not standalone tracks —
  the bed always provides melodic context.
- **File format.** 44.1 kHz mono OGG Vorbis, q5. Filenames:
  `assets/audio/stems/<sector>/<stem_key>.ogg`.

## Naming + layout

```
assets/audio/stems/
  s1_user_space/
    bed.ogg
    melody_lead.ogg
    ...
  s2_kernel/
    bed.ogg
    ...
```

The `StemMixer` resolves which file to play based on `(sector_palette,
stem_key)`. Missing files are treated as silence so partial sets degrade
gracefully.

## Reduce-motion mode

`StemMixer.update_targets(..., reduce_motion=True)` caps the active
non-bed stems at `REDUCE_MOTION_STEM_LIMIT` (currently 2). Priority order:
`boss → tension_* → melody_*`.

## Testing

`tests/test_phase8_music.py` exercises the mixer with a fake sink. New
archetypes must be added to `ARCHETYPE_STEMS` *and* covered by a test
case before adding new audio files.
