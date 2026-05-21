DCDC Clock Simulator
====================

PyQtGraph timing diagram for the DCDC clock sketch.

Run:

```bat
uv run python main.py
```

Current timing assumptions:

- Main horizontal axis: us
- CDS1: high from 1 us to 15 us by default, editable in the side panel
- CDS2: high from 30 us to 40 us by default, editable in the side panel
- Display range: 0 us to 60 us
- PL_DCDC_CLK1 and 3.3V_DIG: 175 MHz divided clock, divider 84 by default, 50% duty
- Extra empty rows are reserved for up to five additional 3.3V_DIG-style signals
- Fine delay notes: 20 ns and 250 ns
