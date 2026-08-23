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

### Rule 0 — you never *choose* whether a name is local or global

This is not a convention, it is the language: **`pp qq rr ss tt uu vv ww xx` are
local. Every other name is global.** There is no prefix to invent and no
ambiguity to resolve — reading `pp` tells you it dies with the translator,
reading `hn` tells you it does not. The convention below only decides *which*
you should reach for, and how to organise the globals.

### Rule 1 — default to a local, and give each of the nine a fixed job

If a value is born and dies inside one translator's rule chain, use a local.
Two translators both using `pp` can never interfere, so you only ever need to
disambiguate *within* a single translator. Nine slots is plenty for that — the
point is to always use them the same way:

| local | job |
|---|---|
| `rr` | first data byte of the message — note number, controller number, pitch-bend value |
| `pp` | second data byte — velocity, controller value |
| `qq` | MIDI channel |
| `ss` `tt` `uu` | scratch: intermediate arithmetic, never emitted |
| `vv` `ww` | values to emit when they are neither `rr` nor `pp` |
| `xx` | flag / spare |

So *"I need two controller values in one translator"* → `pp` for the first and
`vv` for the second; a third goes in `ww`. If one of them is a controller
**number** rather than a value, it belongs in `rr`.

**Most variables in a typical project should be locals.** Reach for a global
only when a value genuinely has to outlive the translator that computed it —
and check first: a translator that captures its own input does *not* need one.

### Rule 2 — put the legend where the variables are used

`pp` and `rr` carry no meaning on their own, and no convention can give them
any: the nine names are imposed by the language. What a fixed job table buys
you is meaning **by position** — the same trade every assembly language makes
with `sp` and `pc`. It works because the set is tiny, closed and always used
the same way. It does not survive someone reading one translator in isolation,
so write the legend down in the three places Bome will show it back to you:

* **the translator name** — append the slot legend to what the translator does:
  `Tilt -> Mod/Foot  [rr=cc# pp=value]`. This is the line you see in the list.
* **a comment rule at the top of the chain** — Bome's rule editor has a Comment
  rule type. Make it the first rule: `; rr = target CC, pp = scaled value`.
  It sits exactly where the arithmetic is, which is where the question comes up.
* **the preset's Comments field** — for anything global the preset owns, and
  for the head letter it has been given.

A translator whose chain is longer than a couple of rules and has no legend is
the one you will misread in six months.

### Rule 3 — a global is owned by exactly one domain

Give each *device or concern* its own head letter, and never share it. You get
exactly ten heads — `g h i j k l m n y z` — so pick the mnemonic ones first and
treat the rest as spares you assign and write down:

| head | mnemonic | typical owner |
|---|---|---|
| `g` | **G**lobal | project-wide state: transpose, current song, active layer |
| `k` | **K**eyboard | the main keyboard |
| `m` | **M**outh | breath / wind controller |
| `h` | **H**ost | the DAW |
| `l` | **L**ights | lighting, LED feedback, scene state |
| `n` | **N**etwork | BomeBox, RTP-MIDI, remote gear |
| `i` | **I**nput 2 | second keyboard or pad controller |
| `j` `y` `z` | — | spares: no natural mnemonic, assign and document |

Ten heads is not many and four of them have no obvious mnemonic, so the letter
alone will never be self-explanatory — that is what Rule 7 is for. What the head
letter must never encode is a **position**: it maps to the device, never to
`Preset.7`. Presets and translators get renumbered the moment you drag one; a
keyboard does not.

### Rule 4 — for globals, the second character carries the type

(Locals have fixed names, so this applies to globals only — their job is set by
the table in Rule 1.)

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

### Rule 5 — never put a shared global in the controller-number slot

A wrong value in the *value* slot gives you a strange setting. A wrong value in
the *number* slot fires a random controller — including the reserved 120–127
range that silences your rig. If the number must be computed, compute it into a
variable **written by that translator only**, and assign it before any exit path.

### Rule 6 — assign before every exit, or don't emit

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

### Rule 7 — name presets and translators by what they are, never by where they are

Same reasoning as the head letters: `Preset.7` and `Translator 3` move the
moment you drag something. Never put an index, an order word (*first*, *then*)
or a state that the UI already shows (*Disabled …* — there is a checkbox for
that, and the name goes stale the day you re-enable it) into a name.

**Presets** own a device or a concern, so name them after it and show the head
letter they own:

```
<device or concern> — <what it routes>  [<head>]

Keyboard — notes to DAW        [k]
Breath — head motion to CC     [m]
Lights — scene feedback        [l]
```

When several presets are **mutually exclusive modes** of the same thing, lead
with the mode so they sort together and the odd one out is obvious:

```
[Violin] Keyboard — notes to DAW   [k]
[Organ]  Keyboard — notes to DAW   [k]
```

**Translators** are one incoming → one outgoing, so the name should answer
"what comes in, what goes out" without opening it, and carry the slot legend
from Rule 2:

```
<incoming> -> <outgoing>   [<slot legend>]

Note on -> DAW ch2            [rr=note pp=vel]
CC13 tilt -> CC1/CC4          [rr=cc# pp=value]
CC13 tilt -> CC80 fall        [vv=flag]
```

Write the **concrete MIDI** — `CC13`, `Note on`, `PB` — not a paraphrase of it.
And when several translators fire on the **same incoming event**, start all of
their names with that same trigger, as in the two `CC13 tilt` lines above. They
then group visually, which is the only warning you get that they share state and
will run in an order you did not choose.

### Rule 8 — document the mapping in the preset

Each preset has a `Comments` field. Put its head letter and the meaning of each
variable there. It travels with the project and survives renumbering.

## A worked example

A wind controller sends head tilt on CC13. Tilting left should move the mod
wheel (CC1), tilting right the foot controller (CC4), with a dead zone around
the centre where nothing should be sent. One incoming event, one outgoing
action, a variable controller number — the shape that goes wrong most often.

### Before

```
Preset:      Breath Control
Translator:  Tilt to Mod and Foot (CC13 to CC1/4)

Incoming:    Control Change, any channel, CC13, value -> ma

Rules:       mf=10
             sg=1
             ma=ma-64                  ; distance from centre
             if(ma<0)sg=-1             ; remember the direction
             ma=ma*sg
             ma=ma-mf                  ; subtract the dead zone
             if(ma<0)ma=0
             if(ma==0)execute          ; (1)
             if(sg==1)mf=63-mf
             if(sg==-1)mf=64-mf
             ma=ma*127
             ma=ma/mf                  ; rescale to 0..127
             mc=1                      ; (2) mod wheel
             if(sg==1)execute
             mc=4                      ;     foot controller

Outgoing:    Control Change, channel 2, controller = mc, value = ma
```

Three defects, and they compound:

* `ma`, `mc`, `mf`, `sg` are **globals** (heads `m` and `s`). Every other
  translator in the project that uses those names writes into the same boxes.
  In a preset where five translators all capture into `ma`, whichever incoming
  message arrived last wins — and messages from one device interleave.
* **(2)** `mc` — the controller **number** — is assigned near the end of the
  chain, but **(1)** exits and fires the outgoing action long before that. On
  the dead-zone branch the translator emits `CC <whatever mc held> = 0`.
* Because `mc` is global, "whatever it held" is not bounded by this
  translator. Anything that lands in the 120–127 range makes the outgoing
  action a **Channel Mode message** — All Sound Off, All Notes Off, Poly On.
  The rig goes quiet and nothing in the MIDI monitor looks like a cause.

### After

```
Preset:      Breath — head motion to CC  [m]
Translator:  CC13 tilt -> CC1/CC4   [rr=cc# pp=value]

Incoming:    Control Change, any channel, CC13, value -> pp

Rules:       ; rr = target CC number, pp = scaled value, ss/tt = scratch
             rr=1                      ; assigned FIRST: valid on every exit
             ss=10
             tt=1
             pp=pp-64
             if(pp<0)tt=-1
             pp=pp*tt
             pp=pp-ss
             if(pp<0)pp=0
             if(pp==0)noexecute        ; dead zone: send NOTHING
             if(tt==1)ss=63-ss
             if(tt==-1)ss=64-ss
             pp=pp*127
             pp=pp/ss
             if(tt==1)execute
             rr=4

Outgoing:    Control Change, channel 2, controller = rr, value = pp
```

What changed, rule by rule:

| | |
|---|---|
| Rule 1 | `ma mc mf sg` → `pp rr ss tt`. All four are **locals**, so a sibling translator using `pp` cannot touch this one. The translator captures its own input, so it needed no global at all. |
| Rule 1 | the slots follow their fixed jobs: `rr` is the controller number, `pp` the value, `ss`/`tt` scratch. |
| Rule 2 | the first rule is a **Comment** stating the legend, and the translator name repeats it. |
| Rule 6 | `if(pp==0)execute` → **`noexecute`**. The branch means "nothing to send", so it sends nothing. |
| Rule 6 | `rr=1` moved to the top, so even a future early exit fires with a valid controller number. Belt and braces — `noexecute` already covers today's path. |
| Rule 7 | the names say what comes in and what goes out, with no index in sight. |

`audit.py` flags the "before" version on three of its checks and the "after"
version on none.

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
