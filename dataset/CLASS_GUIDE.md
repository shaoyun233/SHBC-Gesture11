# Class Guide and Recognition Notes

The official class order below is fixed. Training, inference, and release metadata must use the same indices.

## 0. `back` / Backward

- Group: control gesture
- Meaning: continuous hand movement commanding backward motion
- Data: 145 original sequences, 145 valid sequences, 25,701 frames, and 2,217 windows
- Recognition note: shares transitional hand shapes with `forward`; motion direction is the primary discriminator

## 1. `else` / Other

- Group: non-target gesture
- Meaning: gestures or movements outside the other ten target classes
- Data: 30 original sequences, 30 valid sequences, 5,784 frames, and 504 windows
- Recognition note: the smallest and most internally diverse class; future dataset versions should prioritize its expansion

## 2. `five` / Five

- Group: numeric gesture
- Meaning: a dynamic numeric gesture involving five extended fingers
- Data: 70 original sequences, 70 valid sequences, 17,457 frames, and 1,571 windows
- Recognition note: finger extension and motion trajectory jointly distinguish the class

## 3. `forward` / Forward

- Group: control gesture
- Meaning: continuous hand movement commanding forward motion
- Data: 105 original sequences, 105 valid sequences, 18,125 frames, and 1,554 windows
- Recognition note: distinguished from `back` primarily by opposite motion direction

## 4. `left` / Turn Left

- Group: control gesture
- Meaning: continuous hand movement commanding a left turn
- Data: 110 original sequences, 110 valid sequences, 20,663 frames, and 1,797 windows
- Recognition note: forms an opposing directional pair with `right`

## 5. `one` / One

- Group: numeric gesture
- Meaning: a dynamic single-finger numeric gesture
- Data: 70 original sequences, 70 valid sequences, 18,509 frames, and 1,669 windows
- Recognition note: single-finger pose, flexion, and temporal variation are important cues

## 6. `right` / Turn Right

- Group: control gesture
- Meaning: continuous hand movement commanding a right turn
- Data: 79 original sequences, 79 valid sequences, 14,780 frames, and 1,286 windows
- Recognition note: forms an opposing directional pair with `left`

## 7. `skip` / Jump

- Group: control gesture
- Meaning: continuous command gesture that makes the controlled entity jump
- Data: 171 original sequences, 171 valid sequences, 23,268 frames, and 1,913 windows
- Recognition note: the gesture is comparatively short and can be sensitive to temporal-window boundaries

## 8. `stop` / Stop

- Group: control gesture
- Meaning: command gesture that stops the controlled entity
- Data: 129 original sequences, 127 valid sequences, 22,616 frames, and 1,892 windows
- Recognition note: contains many near-static windows; motion gating can be used, but incorrect suppression must be avoided

## 9. `three` / Three (Sprint)

- Group: numeric gesture
- Meaning: a dynamic three-finger numeric gesture; mapped to sprint in the control application
- Data: 74 original sequences, 74 valid sequences, 18,203 frames, and 1,618 windows
- Recognition note: local hand shapes can resemble those of `two`

## 10. `two` / Two

- Group: numeric gesture
- Meaning: a dynamic two-finger numeric gesture
- Data: 75 original sequences, 75 valid sequences, 17,675 frames, and 1,581 windows
- Recognition note: local hand shapes can resemble those of `three`
