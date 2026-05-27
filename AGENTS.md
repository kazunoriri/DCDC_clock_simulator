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

## Git / GitHub

- このリポジトリは GitHub CLI (`gh`) を使って HTTPS 経由で `git push` できるように設定済み。

```text
origin  https://github.com/kazunoriri/DCDC_clock_simulator.git
```

- GitHub CLI の Git 操作プロトコル: `https`

### 別環境での初回セットアップ手順

```sh
brew install gh
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git remote set-url origin https://github.com/kazunoriri/DCDC_clock_simulator.git
```

`gh auth login` では、ブラウザで GitHub のデバイス認証を行う。

### 確認コマンド

```sh
gh auth status
git remote -v
git push origin main
```

正常なら、変更がない場合は次のように表示される。

```text
Everything up-to-date
```

### よくあるエラー

HTTPS 認証未設定の状態では、次のエラーで `git push` が失敗する。

```text
fatal: could not read Username for 'https://github.com': Device not configured
```

この場合は `gh auth login` と `gh auth setup-git` を実行する。

## Development Notes（設計メモ・将来の改善方針）

このアプリの最終目的は、PL_DCDC_CLK1 の遅延をパラメータとして、CDS1/CDS2 の立ち下がりから 3.3V_DIG の立ち上がり/立ち下がりまでの時間を計算し、その時間余裕が最大となる PL_DCDC_CLK1 遅延を求めること。

### 1. PL_DCDC_CLK1 遅延を 3.3V_DIG に反映する

現在の実装では、PL_DCDC_CLK1 の遅延入力は PL_DCDC_CLK1 の描画には反映されるが、3.3V_DIG のエッジ時刻には反映されていない。

最終目的から見ると、3.3V_DIG の位相は PL_DCDC_CLK1 遅延に従属するべき。

想定する形:

```text
PL_DCDC_CLK1 start = PL_DCDC_CLK1 delay
3.3V_DIG start = PL_DCDC_CLK1 delay + 3.3V_DIG internal delay
```

3.3V_DIG internal delay は現在の固定値 20 ns に相当する可能性がある。

### 2. 最大化する評価値を定義する

現在の表示は、CDS1/CDS2 の立ち下がりから最も近い 3.3V_DIG 立ち上がり/立ち下がりまでの差分を出している。

最適な PL_DCDC_CLK1 遅延を求めるには、評価関数を明確にする必要がある。

安全余裕を見る目的なら、次のようなスコアが自然。

```text
score(delay) = min(
  abs(CDS1 fall - nearest 3.3V_DIG rise),
  abs(CDS1 fall - nearest 3.3V_DIG fall),
  abs(CDS2 fall - nearest 3.3V_DIG rise),
  abs(CDS2 fall - nearest 3.3V_DIG fall)
)
```

この score が最大となる PL_DCDC_CLK1 delay を探す。

### 3. 描画処理と計算処理を分離する

現在は draw() の中で波形描画と距離計算が混ざっている。

最適遅延探索を入れるなら、タイミング計算を UI から独立した関数に切り出すべき。

想定する構造:

```text
timing_model(pl_delay_ns, divider, cds1_fall_us, cds2_fall_us)
  -> 3.3V_DIG edge times
  -> deltas from CDS falling edges
  -> score

find_best_pl_delay(...)
  -> delay candidates を走査
  -> score 最大の delay を返す
```

draw() は計算結果を受け取って描画と右側表示を更新するだけにする。

### 優先順位

1. 3.3V_DIG の開始時刻を PL_DCDC_CLK1 遅延に連動させる
2. 最大化する評価値を `min(abs(...))` ベースで定義する
3. 計算ロジックを描画から切り出す
4. PL_DCDC_CLK1 delay を走査し、score 最大の遅延を表示する
