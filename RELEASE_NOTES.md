# SHBC-Gesture11 v1.0.0

Eleven-class right-hand dynamic gesture dataset and real-time application suite for single-hand biomimetic control.

- 1,058 source sequences and 202,781 ordered JPEG frames from seven participants; source videos are not distributed.
- Dataset metadata, fixed video-level splits, SHA-256 manifests and shard downloader.
- Twenty ZIP frame shards distributed as Release assets, separately from Git history.
- Validation-selected 134-D KMD-Transformer deployment checkpoint (seed 2026).
- Linux camera recognition and browser-based third-person 3D character control.
- Causal stop-hold gate, confidence policy, temporal smoothing, local recognition preview.
- Paper architecture and real-time control diagrams in SVG, PDF and PNG.

Download and verify:

```bash
python dataset/scripts/download_dataset.py --repo shaoyun233/SHBC-Gesture11 --tag v1.0.0 --extract
python dataset/scripts/verify_dataset.py --check-frames
```

Use the fixed video-level splits. The 1,056 quality-filtered sequences used for model experiments differ from the 1,058 source sequences distributed as frames. This application release does not include the complete training experiment suite. See the repository for licenses, dataset scope, third-party notices and application instructions.

Licenses: original code and KMD checkpoint, MIT; dataset and original diagrams, CC BY 4.0. Third-party assets retain their own licenses.
