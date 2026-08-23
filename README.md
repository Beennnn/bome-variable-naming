# A naming convention for Bome MIDI Translator Pro variables

Bome MIDI Translator Pro gives you two-character variable names and almost no
guard rails. `ma`, `oo`, `pp`, `sg` — the names carry no scope, no type and no
owner. On a small project that is fine. On a live rig with a dozen presets and
several controllers played at once, two translators quietly write the same box
and you get a bug that is very hard to see: a controller number computed from a
velocity, a value that arrives one event late, a "dead zone" that fires an
outgoing action it was supposed to suppress.

This repository proposes a convention that makes those collisions impossible by
construction, and an audit script that finds the ones you already have.

## The problem, concretely

A single shared global is enough to turn an expression sweep into a stream of
**Channel Mode messages**. If a translator's Outgoing Action puts a *variable*
in the controller-number slot:

```
Outgoing: Control Change, channel 2, controller = <var>, value = <var>
```

…and `<var>` is a global that another translator writes with unrelated data,
the translator emits `CC <arbitrary> = <arbitrary>`. Sweep through the
120–127 range and you are sending **All Sound Off (120)**, **All Notes Off
(123)** and **Poly Mode On (127)** to every instrument downstream. The symptom
is "the sound just stops", which nobody attributes to a naming problem.

## What Bome actually gives you

Two families, and they are *not* symmetric:

| Family | Names | Lifetime |
|---|---|---|
| **Local** | `pp` `qq` `rr` `ss` `tt` `uu` `vv` `ww` `xx` — **only these nine** | one execution of one translator, per incoming event |
| **Global** | second character appended to heads `g h i j k l m n y z` (e.g. `ga`–`gz`, `g0`–`g9`, `ma`–`mz`, …) | as long as MIDI Translator runs; 0 at project start |

Two consequences most projects get wrong:

1. **Locals are only the nine doubled names.** `pc`, `sg`, `tp`, `oo`, `v1` look
   local — they are not in the local list. Their scope is undocumented, and in
   practice they behave like globals. Every one of them is a latent collision.
2. **Locals are local *per incoming event*.** Two simultaneous messages hitting
   the same translator run it twice with separate copies. That is exactly the
   isolation you want for scratch arithmetic, and you get it for free.

Sources: the Bome manual and forum threads listed at the bottom. Some of the
range details come from forum posts rather than the manual — verify against your
own version before relying on them.

## The convention

### Rule 1 — default to a local

If a value is born and dies inside one translator's rule chain, it must be one
of `pp qq rr ss tt uu vv ww xx`. Nine slots is plenty for one chain, and two
translators using `pp` can never interfere. **Most variables in a typical project
should be locals.** Reach for a global only when a value genuinely has to
outlive the translator.

### Rule 2 — a global is owned by exactly one domain

Give each *device or concern* its own head letter, and never share it:

```
g…  cross-cutting project state (transpose, current song, active layer)
h…  keyboard 1          l…  breath / wind controller
i…  keyboard 2          m…  pedals
j…  pad controller      n…  the DAW
```

The head letter maps to the **device**, never to `Preset.7`. Presets and
translators get renumbered when you drag them around; a device does not.

### Rule 3 — the second character carries the type

| char | type | range |
|---|---|---|
| `n` | note number | 0–127 |
| `v` | velocity / aftertouch | 0–127 |
| `c` | **controller number** (CC#) | 0–127 |
| `a` | controller value, 7-bit | 0–127 |
| `p` | pitch bend, 14-bit | −8192…8191 |
| `h` | MIDI channel | 1–16 |
| `0`–`9` | scratch — no guaranteed type | — |

`hn` is "keyboard 1, note number". `lc` is "breath controller, CC number".
When you read `Outgoing: CC <lc> = <la>` you can tell at a glance that the
controller number comes from the breath domain and is a controller number —
not a velocity that wandered in.

### Rule 4 — never put a shared global in the controller-number slot

A wrong value in the *value* slot gives you a strange setting. A wrong value in
the *number* slot fires a random controller — including the reserved 120–127
range that silences your rig. If the number must be computed, compute it into a
variable **written by that translator only**, and assign it before any exit path.

### Rule 5 — assign before every exit, or don't emit

Bome offers two ways to leave a rule chain early:

```
if(xx==0)execute      → leave the rules AND fire the Outgoing Action
if(xx==0)noexecute    → leave the rules and fire NOTHING
```

`execute` on a dead-zone branch fires the outgoing action with whatever the
variables happen to hold — often values from the previous pass. If the branch
means "nothing to send", it must be `noexecute`. If it means "send the neutral
value", every variable the outgoing action reads must already be assigned at
that point in the chain.

### Rule 6 — document the mapping in the preset

Each preset has a `Comments` field. Put its head letter and the meaning of each
variable there. It travels with the project and survives renumbering.

## Auditing a project you did not write

`.bmtp` files are plain text. `audit.py` reads one and reports:

* every variable, classified as local / global / **outside both ranges**;
* variables written by more than one active preset — the actual collisions;
* variables read in a preset without being written there — de-facto globals,
  which is fine only if that is deliberate;
* variables read but never written anywhere — dead or always zero;
* Outgoing Actions with a variable in the controller-number slot;
* rule chains whose early `execute` precedes the assignment it depends on.

```bash
python3 audit.py "MyProject.bmtp"
```

It only reads. Back your project up before changing anything, and reload it in
MIDI Translator afterwards — the app holds the project in memory and will
overwrite your file when it next saves.

## Status

Proposal, not gospel. The scope ranges are assembled from the manual and forum
threads; corrections and counter-examples are welcome as issues.

## Sources

* [Bome MIDI Translator Pro — user manual](https://download.bome.com/manuals/miditranslator_manual.pdf)
* [What can I do with the variables? (pp, g2, hn, etc…)](https://www.bome.com/forums/3/11876/what-can-i-do-with-the-variables-pp-g2-hn-etc/)
* [Global Variable Reference](https://www.bome.com/forums/3/12092/global-variable-reference/)
* [Initializing global variables](https://forum.bome.com/t/initializing-global-variables/1266)
* [Global variables](https://forum.bome.com/t/global-variables/1600)
* [I ran out of global variables](https://www.bome.com/forums/3/5193/i-ran-out-of-global-variables/)

## License

0BSD — do what you like with it.
