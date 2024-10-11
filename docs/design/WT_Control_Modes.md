Table with the valid control modes in the tool by family, level and type of test:

| OC type   |  Level  | PfFlag | Vflag | Qflag | RefFlag | MqG | MwpqMode | Family | Option | Functionality                                                                                                         |
|-----------|:-------:|:------:|:-----:|:-----:|:-------:|:---:|:--------:|:------:|:------:|-----------------------------------------------------------------------------------------------------------------------|
| USetPoint |  Plant  |   0    | 1     | 1     | 1       | -   | -        | WECC   |   1    | Plant level V Control + coordinated local Q/V control                                                                 |
|           |         |   0    | N/A   | 0     | 1       | -   | -        |        |   2    | Plant level V control                                                                                                 |
|           |         |   -    | -     | -     | -       | 1   | 2        | IEC    |   1    | UQ static. Magnitude controlled is Voltage, Setpoint is UWPRefPu.                                                     |
|           |         |   -    | -     | -     | -       | 2   | 2        |        |   2    | UQ static (open loop reactive power control at turbine level). Magnitude controlled is Voltage, Setpoint is UWPRefPu. |
|           |         |   -    | -     | -     | -       | 0   | 3        |        |   3    | Voltage control: Uref = U + lambda Q. Magnitude controlled is Voltage, Setpoint is UWPRefPu.                          |
|           | Turbine |   0    | 1     | 1     | -       | -   | -        | WECC   |   1    | Local coordinated Q/V control only                                                                                    |
|           |         |   0    | 0     | 1     | -       | -   | -        |        |   2    | Local V control only                                                                                                  |
|           |         |   -    | -     | -     | -       | 0   | -        | IEC    |   1    | Voltage control                                                                                                       |
| QSetPoint |  Plant  |   0    | 1     | 1     | 0       | -   | -        | WECC   |   1    | Plant level Q Control + coordinated local Q/V control                                                                 |
|           |         |   0    | N/A   | 0     | 0       | -   | -        |        |   2    | Plant level Q control                                                                                                 |
|           |         |   -    | -     | -     | -       | 1   | 0        | IEC    |   1    | Reactive power control. Magnitude controlled is Reactive, Setpoint is QWPRefPu.                                       |
|           |         |   -    | -     | -     | -       | 2   | 0        |        |   2    | Reactive power control (open loop at turbine level). Magnitude controlled is Reactive, Setpoint is QWPRefPu.          |
|           | Turbine |   0    | 1     | 1     | -       | -   | -        | WECC   |   1    | Local coordinated Q/V control only                                                                                    |
|           |         |   0    | N/A   | 0     | -       | -   | -        |        |   2    | Constant Q control                                                                                                    |
|           |         |   -    | -     | -     | -       | 1   | -        | IEC    |   1    | Reactive power control                                                                                                |
|           |         |   -    | -     | -     | -       | 2   | -        |        |   2    | Open loop reactive power control                                                                                      |


Setpoint parameter names in dynamic models:

| OC type   |  Family  |  Level  | Init. Setpoint | Setpoint   |
|-----------|:--------:|:-------:|:--------------:|:----------:|
| USetPoint |   WECC   |  Plant  |    URef0Pu     |   URefPu   |
|           |          | Turbine |    VRef1Pu     | VRefConst1 |
|           | IEC 2015 |  Plant  |      U0Pu      |  UWPRefPu  |
|           |          | Turbine |      U0Pu      |  UWPRefPu  |
|           | IEC 2020 |  Plant  |      U0Pu      |  xWPRefPu  |
|           |          | Turbine |      U0Pu      |  UWPRefPu  |
| QSetPoint |   WECC   |  Plant  |    QGen0Pu     |   QRefPu   |
|           |          | Turbine |    QInj0Pu     | QInjRefPu  |
|           | IEC 2015 |  Plant  |      Q0Pu      |  QWPRefPu  |
|           |          | Turbine |      Q0Pu      |  QWPRefPu  |
|           | IEC 2020 |  Plant  |      Q0Pu      |  xWPRefPu  |
|           |          | Turbine |      Q0Pu      |  QWPRefPu  |

