DCDC Clock Simulator
====================

PyQtGraph timing diagram for the DCDC clock sketch.

Run:

```bat
uv run python main.py
```

Startup configuration:

- At startup, `timing_config_debug.xlsx` is loaded when it exists.
- When `timing_config_debug.xlsx` does not exist, the app starts with empty plots.
- Any `.xlsx` file name can be loaded by dragging and dropping it onto the window.

Configuration Excel:

Use the `config` sheet with two columns: `parameter` and `value`.

| parameter | value |
| --- | --- |
| pl_dcdc_clk_name | PL_DCDC_CLK1 |
| pl_dcdc_clk_delay_clks | 3 |
| pl_dcdc_clk_delay_ns | =ROUND((1/175)*B3*10^3,1) |
| gate_period_us | 60.0 |
| cds1_rise_us | 1.0 |
| cds1_fall_us | 15.0 |
| cds2_rise_us | 30.0 |
| cds2_fall_us | 40.0 |
| clock_div_ratio | 84 |
| clock_frequency_MHz | =ROUND(175/B34,2) |
| power_net_name_0 | 3.3V_DIG |
| power_net_name_1 | 3.3V_DIG_2 |
| power_net_name_2 | 3.3V_DIG_3 |
| power_net_name_3 | 3.3V_DIG_4 |
| power_net_name_4 | 3.3V_DIG_5 |
| power_net_name_5 | 3.3V_DIG_6 |
| power_net_name_6 |  |
| power_net_name_7 |  |
| power_net_delay_ns_0 | 0.0 |
| power_net_delay_ns_1 | 10.0 |
| power_net_delay_ns_2 | 20.0 |
| power_net_delay_ns_3 | 30.0 |
| power_net_delay_ns_4 | 40.0 |
| power_net_delay_ns_5 | 50.0 |
| power_net_delay_ns_6 |  |
| power_net_delay_ns_7 |  |
| power_net_duty_percent_0 | 35.0 |
| power_net_duty_percent_1 | 42.5 |
| power_net_duty_percent_2 | 50.0 |
| power_net_duty_percent_3 | 57.5 |
| power_net_duty_percent_4 | 65.0 |
| power_net_duty_percent_5 | 72.5 |
| power_net_duty_percent_6 |  |
| power_net_duty_percent_7 |  |

Current timing assumptions:

- Main horizontal axis: us
- Signal names, gate period, CDS timing, and divider are loaded from Excel
- Display range: 0 us to `gate_period_us`
- PL_DCDC_CLK1: 175 MHz divided clock, 50% duty
- `pl_dcdc_clk_delay_ns` is the initial PL_DCDC_CLK1 delay in ns
- `power_net_delay_ns_*` values are ns delays from PL_DCDC_CLK1
- `power_net_duty_percent_*` values are power net waveform duty percentages
- Power nets are not plotted when their name is blank, or delay/duty is missing or invalid
- PL_DCDC_CLK1: delay is editable in ns from the side panel
- 3.3V_DIG: nearest rising/falling edge distance from CDS1/CDS2 falling edges is shown in ns
- Up to eight power net signals can be loaded
- Fine delay notes: 20 ns and 250 ns
