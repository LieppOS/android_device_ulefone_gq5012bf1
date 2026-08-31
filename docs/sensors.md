# Sensors

## VERIFIED physical sensors

Stock `dumpsys sensorservice` exposed 22 hardware sensors and identified:

| Function | Android name | Vendor |
|---|---|---|
| Accelerometer | `icm4n607_acc` | `iven_sense` |
| Gyroscope | `icm4n607_gyro` | `iven_sense` |
| Magnetometer | `mmc5603` | `memsic` |
| Ambient light | `stk3a5x_als` | `sensortek` |
| Proximity | `stk3a5x_ps` | `sensortek` |
| Barometer | `spl07` | `goer` |

MediaTek fusion exposes orientation, gravity, linear acceleration, rotation
vectors, uncalibrated accelerometer/gyro/magnetometer, significant motion,
step detector/counter, tilt, wake gesture and device orientation. The stock
snapshot contains real accelerometer events, proving more than declaration.

Stock applications include `YftBarometer`, `YftStepRecord` and
`YftSensorCalibration`; preserving the sensor HAL without its calibration
contract is insufficient.

## UNKNOWN

- Exact sensor-hub firmware/config ownership and persistent calibration paths
  still need a file-level dependency trace.
- Full-ROM batching, wake-up, step persistence and calibration behavior require
  enforcing hardware tests.
