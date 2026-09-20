# A worked example

A wind controller sends head tilt on CC13. Tilting left should move the mod wheel (CC1),
tilting right the foot controller (CC4), with a dead zone around the centre where nothing
should be sent. One incoming event, one outgoing action, a variable controller number —
the shape that goes wrong most often.

The rules referenced below are in [convention.md](convention.md).

## Before

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

* `ma`, `mc`, `mf`, `sg` are **globals** (heads `m` and `s`). Every other translator in
  the project that uses those names writes into the same boxes. In a preset where five
  translators all capture into `ma`, whichever incoming message arrived last wins — and
  messages from one device interleave.
* **(2)** `mc` — the controller **number** — is assigned near the end of the chain, but
  **(1)** exits and fires the outgoing action long before that. On the dead-zone branch
  the translator emits `CC <whatever mc held> = 0`.
* Because `mc` is global, "whatever it held" is not bounded by this translator. Anything
  that lands in the 120–127 range makes the outgoing action a **Channel Mode message** —
  All Sound Off, All Notes Off, Poly On. The rig goes quiet and nothing in the MIDI
  monitor looks like a cause.

## After

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

`audit.py` flags the "before" version on three of its checks and the "after" version on
none.
