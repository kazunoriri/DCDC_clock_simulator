# Agent Notes

## Verification

- Run project verification through the Windows-side project `uv` environment, not the bare WSL Python.
- Use commands from the repository root, for example:

```sh
/mnt/c/Windows/System32/cmd.exe /c uv run python -m py_compile main.py compare_measured_delay_margins.py repair_config_excels.py compare_static_60us_measurements.py estimate_power_net_delays.py
```

- Reason: the bare WSL Python may not have this project's GUI/runtime dependencies such as `pyqtgraph`, while `uv run` uses the project environment declared by `pyproject.toml` and `uv.lock`.
- After any code/config change, launch the app through the Windows-side project `uv` environment and leave it running for the user to inspect. Do not auto-close the GUI unless the user explicitly asks for a non-interactive check.

## Excel Config Files

- Do not save `.xlsx` config files with `openpyxl` after structural edits such as inserting/deleting rows or columns. Excel may report file-level repair errors when opening the workbook.
- For structural Excel edits, restore or copy from a known-good workbook first, then use native Excel COM automation via Windows Python/pywin32 to edit and save.
- After editing `.xlsx` files, verify both:
  - Excel COM can open each workbook and read the `config` sheet.
  - The app can read each workbook through the project `uv` environment.
- Value-only inspection with `openpyxl` is acceptable, but do not use it to save these workbooks after structural changes.
