# Armor lights intent API

ArmorParts (`org.lieppos.armorparts`, system app) accepts broadcast intents
that control the **super flashlight** (white LN2403 camping light) and the
**red** and **blue** LEDs. Only ArmorParts may write the `yft_camplight`
driver nodes, so automation apps use this API.

The receiver is exported and needs no permission: any app on the phone can
switch these lights.

## Actions

| Action | Effect |
|---|---|
| `org.lieppos.armorparts.action.LIGHT` | control one light (extras below) |
| `org.lieppos.armorparts.action.LIGHTS_OFF` | stop every strobe/pattern, all lights off |

## Extras of `action.LIGHT`

Extras may be sent as int/boolean or as strings (`"50"`, `"true"`).

| Extra | Values | Default | Meaning |
|---|---|---|---|
| `light` | `white` (alias `flashlight`, `torch`), `red`, `blue`, `police`, `all` | required | which light |
| `level` | `0`–`100` | `100` | brightness in %; `0` = off |
| `toggle` | `true`/`false` | `false` | off if on, else on at `level`; with a strobe/pattern: stop it if running, else start it |
| `on_ms` | ms (≥ 10) | – | strobe: time on (for `police`: time per colour) |
| `off_ms` | ms (≥ 10) | = `on_ms` | strobe: time off (for `police`: dark gap, default none) |
| `cycles` | count | `0` | stop after N flashes; `0` = until another command |
| `mode` | `blink`, `sos` (white); `flash` (red/blue) | – | built-in driver patterns |

Any new command for a light replaces that light's running strobe or pattern.
A `red`/`blue` command also ends `police`.

Notes:
- `white` brightness maps onto the driver's 94 steps, `red`/`blue` onto
  hardware PWM with 40 steps; `100` is full on.
- `police` without `on_ms` runs the driver's own 40 ms red/blue pattern.
- `mode=blink` is the driver's 50 ms/50 ms blink, `mode=sos` its SOS signal,
  `mode=flash` its 40 ms single-colour flash.
- Strobes keep a fixed timeline, also with the screen off (partial wake lock
  only while one runs). Timing is software, so expect a few ms of jitter;
  below about 20 ms per phase it gets uneven.
- The white light gets hot at high levels. Nothing limits how long it stays on.

## Examples (adb)

```sh
B="adb shell am broadcast -a org.lieppos.armorparts.action.LIGHT"
$B --es light white --ei level 30            # flashlight at 30 %
$B --es light white --ez toggle true         # flashlight on/off
$B --es light red --ei level 5               # dim red
$B --es light blue --ei on_ms 50 --ei off_ms 450          # blue blip every 0.5 s
$B --es light white --ei on_ms 30 --ei off_ms 70 --ei cycles 20   # 10 Hz strobe, 2 s
$B --es light police --ei on_ms 150 --ei off_ms 50        # slow red/blue alternation
$B --es light police --ez toggle true        # driver's fast red/blue pattern on/off
$B --es light white --es mode sos
adb shell am broadcast -a org.lieppos.armorparts.action.LIGHTS_OFF
```

## Tasker

Task → **System → Send Intent**:
- Action: `org.lieppos.armorparts.action.LIGHT`
- Extras: `light:white`, `level:30` (Tasker allows three extras per action,
  e.g. `light:blue`, `on_ms:50`, `off_ms:450`; leave out `off_ms` when it
  equals `on_ms` to make room for `cycles`)
- Target: **Broadcast Receiver**

Brightness from a variable: `level:%par1`.

## MacroDroid

Action → **Connectivity → Send intent**:
- Target: **Broadcast**
- Action: `org.lieppos.armorparts.action.LIGHT`
- Extras: `light` = `red`, `level` = `40`, … (any number of extras)

## Key Mapper

Action → **Send intent** → target **Broadcast receiver**:
- Action: `org.lieppos.armorparts.action.LIGHT`
- Extras: `light` = `white` (String), `toggle` = `true` (Boolean)
