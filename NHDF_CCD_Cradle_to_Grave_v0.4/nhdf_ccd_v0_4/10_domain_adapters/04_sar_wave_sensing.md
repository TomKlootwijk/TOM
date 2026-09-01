# SAR and wave-sensing adapter

## Proposed mapping

- state: complex radar echoes, navigation state, timing and phase residuals;
- event surface: a calibrated focus-consistency or phase-error boundary;
- motion: platform trajectory and propagation model;
- output: focused image and uncertainty/quality metrics.

The CCD contribution is algorithmic: conservative interval search can bracket when a continuous residual crosses a threshold, and bounded queues can partition range/azimuth/subaperture hypotheses. It does not convert wave focusing into rigid-body contact.

Required tests include phase RMSE, point-target resolution, peak/integrated sidelobe ratios, image entropy or contrast, compute cost, dropped frames, and controlled ionospheric disturbances against established autofocus methods.
