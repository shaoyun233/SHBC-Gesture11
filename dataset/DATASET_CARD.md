# Dataset Card

## Intended Use

SHBC-Gesture11 is intended for research on dynamic gesture recognition, temporal landmark modeling, RGB spatiotemporal modeling, and model robustness. The dataset contains 11 classes spanning control gestures, numeric gestures, and an other-gesture class. Its public release consists of 202,781 temporally ordered image frames.

## Data Organization

Each `video_id` identifies one continuously captured sequence. Frame filenames use zero-based, six-digit indices. The official split is defined at the video level to prevent adjacent frames from appearing in both the training and test sets.

## Collection Scope

The data were collected from 7 participants, including 5 male and 2 female participants. The current public release contains right-hand sequences only. The release does not provide a participant-to-video mapping; therefore, the official split ensures independence between video contents but must not be interpreted as a participant-independent evaluation.

## Known Limitations

- The classes are imbalanced, and the `else` class contains substantially fewer samples than the other classes.
- Camera models and detailed environmental/lighting metadata are not included; reproducibility is limited to the supplied frames and sequence metadata.
- Images may contain arms and backgrounds. The data owner confirms that informed consent and privacy/rights clearance for public release and redistribution have been completed.
- Two `stop` sequences have insufficient MediaPipe detection rates and are excluded from the unified training protocol used in the paper; they remain in the original released frames and are explicitly marked.

## Licensing and Ethics

The dataset is licensed under CC BY 4.0; see LICENSE.md in this directory.
The data owner confirmed completion of the participant consent and privacy
review on 2026-11-10. This is the owner's declaration, not a separate audit.
Contact and removal-request procedures are in ../LICENSING.md.
