# SHBC-Gesture11 Image-Frame Dataset

SHBC-Gesture11 contains 11 classes of single-hand dynamic gestures. The public release consists of temporally ordered JPEG image frames and does not include the source videos. Frames retain the 16:9 aspect ratio of the source videos and are not stretched to a square format.

## Dataset Summary

- Classes: `back, else, five, forward, left, one, right, skip, stop, three, two`
- Participants: 7, including 5 male and 2 female participants
- Handedness: right hand only in the current release
- Original sequences: 1,058; valid sequences in the unified benchmark: 1,056
- Image frames: 202,781
- Official sequence-level split: 739 training, 159 validation, and 158 test sequences; 2 additional sequences are excluded because of insufficient hand-detection rates
- Resolution: 1,042 sequences at 1280x720 and 16 sequences at 960x540
- Encoding: JPEG quality 95 with the original aspect ratio preserved

## Extracted Directory Structure

```text
dataset/
  frames/<class>/<video_id>/frame_000000.jpg
  metadata/classes.csv
  metadata/videos.csv
  metadata/frames.csv
  splits/train.txt
  splits/val.txt
  splits/test.txt
```

Adjacent frames from the same sequence must not be randomly divided between the training and test sets. All experiments reported in the paper must use the fixed sequence-level split supplied with the repository.

## Downloading from GitHub Releases

Because the image frames exceed the limits of a regular Git repository, they are distributed as 20 SHA-256-verified ZIP assets in the `v1.0.0` Release. After cloning the repository, run:

```bash
python dataset/scripts/download_dataset.py --repo ShaoyunZong/SHBC-Gesture11 --tag v1.0.0 --extract
python dataset/scripts/verify_dataset.py --check-frames
```

The downloader supports resumable downloads, SHA-256 verification, and path-safe extraction. The assumed public repository is <https://github.com/ShaoyunZong/SHBC-Gesture11>; verify this address before the final release. The complete dataset is not required to run either real-time demo.

Before public release, read `DATASET_CARD.md`, `CLASS_GUIDE.md`, and `LICENSE_PENDING.md` in the repository root.
