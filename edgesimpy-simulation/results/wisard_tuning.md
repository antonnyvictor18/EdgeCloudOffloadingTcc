# WiSARD Hyperparameter Study (6-feature contract)

## Protocol

- Train split: 10500 samples; selection on validation split: 2250 samples. **Test split untouched.**
- Features (frozen contract): CpuCycles, TaskSizeMB, LatencySensitivity, RequiredMemoryMB, BandwidthMbps, NetworkLatencyMs
- Primary selection metric: **macro-F1** (validation). Accuracy reported, not used for selection
  (62/38 class prior makes accuracy reward majority collapse).
- Seeds per configuration (RAM mapping): [7, 11, 23, 42, 101] - mean ± sd reported; selection on the mean.
- Tie-break between configurations: fewer total input bits, then fewer RAM cells written.
- Encoder normalization fitted on train only; residual ties -> Edge (C# convention).

## Search space

- encoding: ['binary', 'thermometer']
- bits_per_feature: [4, 8, 16, 32, 64]
- ram_address_size: [2, 4, 8, 16]
- bleaching: [False, True]
- configurations: 72 x 5 seeds = 360 trainings

## Reference points (validation)

- Majority classifier (always Edge): accuracy 0.6240, macro-F1 0.3842
- MLP_final_6 (frozen artifact): accuracy 0.8156, macro-F1 0.7988, recall Cloud 0.701

## Baseline: C#-equivalent configuration

| encoding | bits | addr | bleach | RAMs | macro-F1 (mean ± sd) | bal. acc | accuracy | recall Cloud | Edge rate | tie rate |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| binary | 4 | 8 | off | 3 | 0.3954 ± 0.0074 | 0.5044 | 0.6268 | 0.011 | 0.995 | 0.816 |

## Selected configuration

| encoding | bits | addr | bleach | RAMs | macro-F1 (mean ± sd) | bal. acc | accuracy | recall Cloud | Edge rate | tie rate |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| thermometer | 64 | 16 | on | 24 | 0.7381 ± 0.0093 | 0.7293 | 0.7675 | 0.576 | 0.711 | 0.000 |

Improvement over baseline: macro-F1 0.3954 -> 0.7381 (+0.3426); recall Cloud 0.011 -> 0.576; tie rate 0.816 -> 0.000.

Per-seed (selected):

| seed | macro-F1 | bal. acc | accuracy | recall Cloud | Edge rate | tie rate | confusion [[Cloud,Edge],[Cloud,Edge]] |
|---:|---:|---:|---:|---:|---:|---:|---|
| 7 | 0.7448 | 0.7367 | 0.7711 | 0.598 | 0.697 | 0.000 | [[1229, 175], [340, 506]] |
| 11 | 0.7327 | 0.7239 | 0.7636 | 0.564 | 0.716 | 0.000 | [[1241, 163], [369, 477]] |
| 23 | 0.7496 | 0.7408 | 0.7764 | 0.597 | 0.704 | 0.000 | [[1242, 162], [341, 505]] |
| 42 | 0.7230 | 0.7139 | 0.7573 | 0.539 | 0.728 | 0.000 | [[1248, 156], [390, 456]] |
| 101 | 0.7402 | 0.7314 | 0.7689 | 0.580 | 0.708 | 0.000 | [[1239, 165], [355, 491]] |

## Marginal effects (mean macro-F1 by level, averaged over other dimensions)

- **encoding**: binary=0.5407, thermometer=0.5566
- **bits_per_feature**: 16=0.5423, 32=0.5470, 4=0.5465, 64=0.5829, 8=0.5457
- **ram_address_size**: 16=0.5970, 2=0.5181, 4=0.5296, 8=0.5535
- **bleaching**: False=0.4320, True=0.6671

## Top 15 configurations

| encoding | bits | addr | bleach | RAMs | macro-F1 (mean ± sd) | bal. acc | accuracy | recall Cloud | Edge rate | tie rate |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| thermometer | 64 | 16 | on | 24 | 0.7381 ± 0.0093 | 0.7293 | 0.7675 | 0.576 | 0.711 | 0.000 |
| thermometer | 32 | 16 | on | 12 | 0.7301 ± 0.0131 | 0.7220 | 0.7604 | 0.567 | 0.710 | 0.000 |
| binary | 4 | 8 | on | 3 | 0.7299 ± 0.0196 | 0.7213 | 0.7636 | 0.550 | 0.726 | 0.000 |
| thermometer | 64 | 8 | on | 48 | 0.7250 ± 0.0054 | 0.7153 | 0.7607 | 0.532 | 0.736 | 0.000 |
| thermometer | 8 | 16 | on | 3 | 0.7227 ± 0.0085 | 0.7174 | 0.7484 | 0.592 | 0.679 | 0.001 |
| thermometer | 16 | 16 | on | 6 | 0.7139 ± 0.0086 | 0.7061 | 0.7474 | 0.539 | 0.718 | 0.000 |
| thermometer | 32 | 8 | on | 24 | 0.7135 ± 0.0122 | 0.7045 | 0.7520 | 0.513 | 0.742 | 0.000 |
| binary | 8 | 2 | on | 24 | 0.7069 ± 0.0068 | 0.6976 | 0.7532 | 0.473 | 0.774 | 0.000 |
| thermometer | 8 | 8 | on | 6 | 0.7059 ± 0.0015 | 0.6987 | 0.7411 | 0.528 | 0.720 | 0.000 |
| thermometer | 16 | 8 | on | 12 | 0.7051 ± 0.0166 | 0.6964 | 0.7474 | 0.491 | 0.754 | 0.000 |
| binary | 8 | 8 | on | 6 | 0.7049 ± 0.0200 | 0.6964 | 0.7499 | 0.481 | 0.764 | 0.000 |
| binary | 4 | 4 | on | 6 | 0.6960 ± 0.0194 | 0.6883 | 0.7448 | 0.460 | 0.775 | 0.000 |
| thermometer | 4 | 16 | on | 2 | 0.6954 ± 0.0082 | 0.6897 | 0.7298 | 0.528 | 0.709 | 0.006 |
| binary | 4 | 2 | on | 12 | 0.6923 ± 0.0156 | 0.6847 | 0.7428 | 0.451 | 0.780 | 0.000 |
| binary | 16 | 2 | on | 48 | 0.6895 ± 0.0194 | 0.6824 | 0.7420 | 0.442 | 0.786 | 0.000 |

## All configurations

| encoding | bits | addr | bleach | RAMs | macro-F1 (mean ± sd) | bal. acc | accuracy | recall Cloud | Edge rate | tie rate |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| thermometer | 64 | 16 | on | 24 | 0.7381 ± 0.0093 | 0.7293 | 0.7675 | 0.576 | 0.711 | 0.000 |
| thermometer | 32 | 16 | on | 12 | 0.7301 ± 0.0131 | 0.7220 | 0.7604 | 0.567 | 0.710 | 0.000 |
| binary | 4 | 8 | on | 3 | 0.7299 ± 0.0196 | 0.7213 | 0.7636 | 0.550 | 0.726 | 0.000 |
| thermometer | 64 | 8 | on | 48 | 0.7250 ± 0.0054 | 0.7153 | 0.7607 | 0.532 | 0.736 | 0.000 |
| thermometer | 8 | 16 | on | 3 | 0.7227 ± 0.0085 | 0.7174 | 0.7484 | 0.592 | 0.679 | 0.001 |
| thermometer | 16 | 16 | on | 6 | 0.7139 ± 0.0086 | 0.7061 | 0.7474 | 0.539 | 0.718 | 0.000 |
| thermometer | 32 | 8 | on | 24 | 0.7135 ± 0.0122 | 0.7045 | 0.7520 | 0.513 | 0.742 | 0.000 |
| binary | 8 | 2 | on | 24 | 0.7069 ± 0.0068 | 0.6976 | 0.7532 | 0.473 | 0.774 | 0.000 |
| thermometer | 8 | 8 | on | 6 | 0.7059 ± 0.0015 | 0.6987 | 0.7411 | 0.528 | 0.720 | 0.000 |
| thermometer | 16 | 8 | on | 12 | 0.7051 ± 0.0166 | 0.6964 | 0.7474 | 0.491 | 0.754 | 0.000 |
| binary | 8 | 8 | on | 6 | 0.7049 ± 0.0200 | 0.6964 | 0.7499 | 0.481 | 0.764 | 0.000 |
| binary | 4 | 4 | on | 6 | 0.6960 ± 0.0194 | 0.6883 | 0.7448 | 0.460 | 0.775 | 0.000 |
| thermometer | 4 | 16 | on | 2 | 0.6954 ± 0.0082 | 0.6897 | 0.7298 | 0.528 | 0.709 | 0.006 |
| binary | 4 | 2 | on | 12 | 0.6923 ± 0.0156 | 0.6847 | 0.7428 | 0.451 | 0.780 | 0.000 |
| binary | 16 | 2 | on | 48 | 0.6895 ± 0.0194 | 0.6824 | 0.7420 | 0.442 | 0.786 | 0.000 |
| thermometer | 4 | 8 | on | 3 | 0.6889 ± 0.0046 | 0.6818 | 0.7318 | 0.480 | 0.747 | 0.000 |
| binary | 32 | 2 | on | 96 | 0.6888 ± 0.0097 | 0.6814 | 0.7419 | 0.438 | 0.789 | 0.000 |
| binary | 32 | 4 | on | 48 | 0.6887 ± 0.0054 | 0.6813 | 0.7416 | 0.438 | 0.788 | 0.000 |
| binary | 8 | 4 | on | 12 | 0.6845 ± 0.0094 | 0.6779 | 0.7413 | 0.422 | 0.800 | 0.000 |
| binary | 16 | 4 | on | 24 | 0.6798 ± 0.0249 | 0.6743 | 0.7366 | 0.423 | 0.795 | 0.000 |
| thermometer | 64 | 4 | on | 96 | 0.6745 ± 0.0059 | 0.6688 | 0.7293 | 0.425 | 0.786 | 0.000 |
| thermometer | 32 | 4 | on | 48 | 0.6730 ± 0.0153 | 0.6677 | 0.7298 | 0.417 | 0.792 | 0.000 |
| thermometer | 8 | 4 | on | 12 | 0.6611 ± 0.0044 | 0.6571 | 0.7196 | 0.405 | 0.791 | 0.000 |
| thermometer | 16 | 4 | on | 24 | 0.6560 ± 0.0108 | 0.6530 | 0.7177 | 0.392 | 0.799 | 0.000 |
| binary | 16 | 8 | on | 12 | 0.6467 ± 0.0225 | 0.6468 | 0.7183 | 0.359 | 0.825 | 0.000 |
| thermometer | 4 | 4 | on | 6 | 0.6428 ± 0.0262 | 0.6427 | 0.7083 | 0.378 | 0.800 | 0.000 |
| thermometer | 64 | 2 | on | 192 | 0.6376 ± 0.0047 | 0.6393 | 0.7132 | 0.341 | 0.833 | 0.000 |
| thermometer | 32 | 2 | on | 96 | 0.6351 ± 0.0177 | 0.6376 | 0.7114 | 0.340 | 0.832 | 0.000 |
| thermometer | 64 | 16 | off | 24 | 0.6340 ± 0.0070 | 0.6378 | 0.7156 | 0.324 | 0.848 | 0.427 |
| binary | 32 | 8 | on | 24 | 0.6312 ± 0.0133 | 0.6344 | 0.7099 | 0.330 | 0.838 | 0.000 |
| binary | 4 | 16 | on | 2 | 0.6259 ± 0.0310 | 0.6243 | 0.6750 | 0.420 | 0.735 | 0.180 |
| thermometer | 8 | 2 | on | 24 | 0.6151 ± 0.0070 | 0.6224 | 0.7016 | 0.303 | 0.850 | 0.000 |
| thermometer | 16 | 2 | on | 48 | 0.6074 ± 0.0160 | 0.6166 | 0.6969 | 0.293 | 0.853 | 0.000 |
| thermometer | 4 | 2 | on | 12 | 0.5947 ± 0.0136 | 0.6070 | 0.6888 | 0.277 | 0.856 | 0.000 |
| thermometer | 32 | 16 | off | 12 | 0.5915 ± 0.0146 | 0.6077 | 0.6950 | 0.256 | 0.879 | 0.504 |
| binary | 4 | 16 | off | 2 | 0.5674 ± 0.0158 | 0.5817 | 0.6615 | 0.260 | 0.842 | 0.502 |
| binary | 8 | 16 | on | 3 | 0.5620 ± 0.0089 | 0.5679 | 0.6324 | 0.308 | 0.777 | 0.358 |
| binary | 8 | 16 | off | 3 | 0.5498 ± 0.0108 | 0.5616 | 0.6348 | 0.266 | 0.810 | 0.440 |
| thermometer | 16 | 16 | off | 6 | 0.5489 ± 0.0074 | 0.5804 | 0.6766 | 0.192 | 0.908 | 0.589 |
| binary | 16 | 16 | on | 6 | 0.5404 ± 0.0132 | 0.5461 | 0.6065 | 0.303 | 0.755 | 0.290 |
| binary | 16 | 16 | off | 6 | 0.5346 ± 0.0115 | 0.5436 | 0.6097 | 0.277 | 0.777 | 0.350 |
| binary | 32 | 16 | on | 12 | 0.5130 ± 0.0059 | 0.5215 | 0.5842 | 0.269 | 0.758 | 0.229 |
| binary | 32 | 16 | off | 12 | 0.5096 ± 0.0039 | 0.5203 | 0.5864 | 0.254 | 0.772 | 0.264 |
| thermometer | 4 | 16 | off | 2 | 0.4857 ± 0.0201 | 0.5459 | 0.6540 | 0.110 | 0.948 | 0.705 |
| thermometer | 8 | 16 | off | 3 | 0.4837 ± 0.0249 | 0.5450 | 0.6535 | 0.107 | 0.949 | 0.717 |
| thermometer | 64 | 8 | off | 48 | 0.4779 ± 0.0081 | 0.5434 | 0.6540 | 0.097 | 0.957 | 0.672 |
| thermometer | 32 | 8 | off | 24 | 0.4357 ± 0.0106 | 0.5227 | 0.6396 | 0.051 | 0.977 | 0.726 |
| thermometer | 16 | 8 | off | 12 | 0.4190 ± 0.0091 | 0.5146 | 0.6338 | 0.034 | 0.984 | 0.790 |
| thermometer | 8 | 8 | off | 6 | 0.3993 ± 0.0062 | 0.5054 | 0.6269 | 0.015 | 0.992 | 0.857 |
| binary | 8 | 8 | off | 6 | 0.3980 ± 0.0097 | 0.5055 | 0.6275 | 0.013 | 0.993 | 0.813 |
| binary | 16 | 8 | off | 12 | 0.3973 ± 0.0048 | 0.5052 | 0.6273 | 0.013 | 0.994 | 0.816 |
| binary | 32 | 8 | off | 24 | 0.3965 ± 0.0064 | 0.5051 | 0.6274 | 0.012 | 0.994 | 0.804 |
| binary | 4 | 8 | off | 3 | 0.3954 ± 0.0074 | 0.5044 | 0.6268 | 0.011 | 0.995 | 0.816 |
| thermometer | 32 | 4 | off | 48 | 0.3923 ± 0.0062 | 0.5036 | 0.6266 | 0.008 | 0.997 | 0.824 |
| thermometer | 4 | 8 | off | 3 | 0.3922 ± 0.0072 | 0.5034 | 0.6263 | 0.008 | 0.997 | 0.882 |
| thermometer | 64 | 4 | off | 96 | 0.3919 ± 0.0028 | 0.5032 | 0.6262 | 0.007 | 0.997 | 0.816 |
| thermometer | 16 | 4 | off | 24 | 0.3854 ± 0.0011 | 0.5004 | 0.6242 | 0.001 | 0.999 | 0.881 |
| thermometer | 32 | 2 | off | 96 | 0.3850 ± 0.0010 | 0.5004 | 0.6243 | 0.001 | 1.000 | 0.892 |
| thermometer | 8 | 4 | off | 12 | 0.3848 ± 0.0008 | 0.5000 | 0.6238 | 0.001 | 0.999 | 0.917 |
| thermometer | 4 | 2 | off | 12 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.994 |
| binary | 4 | 2 | off | 12 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 1.000 |
| binary | 4 | 4 | off | 6 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.981 |
| thermometer | 8 | 2 | off | 24 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.972 |
| binary | 8 | 2 | off | 24 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 1.000 |
| binary | 8 | 4 | off | 12 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.990 |
| thermometer | 16 | 2 | off | 48 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.899 |
| binary | 16 | 2 | off | 48 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 1.000 |
| binary | 16 | 4 | off | 24 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.997 |
| binary | 32 | 2 | off | 96 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 1.000 |
| binary | 32 | 4 | off | 48 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.991 |
| thermometer | 64 | 2 | off | 192 | 0.3842 ± 0.0000 | 0.5000 | 0.6240 | 0.000 | 1.000 | 0.862 |
| thermometer | 4 | 4 | off | 6 | 0.3842 ± 0.0001 | 0.4999 | 0.6238 | 0.000 | 1.000 | 0.950 |

## Notes

- Confusion matrix rows/cols follow sorted labels: [Cloud, Edge].
- `tie rate` = fraction of validation samples whose final decision was a residual tie resolved to Edge.
- `RAMs` = ceil(total_bits / ram_address_size) per discriminator.
- Selection was performed once, on validation, before any test-set or EdgeSimPy evaluation.