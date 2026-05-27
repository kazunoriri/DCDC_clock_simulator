DCDC Clock Simulator
====================

このアプリは、基板上の DCDC コンバータのスイッチング波形について、立ち上がりエッジおよび立ち下がりエッジが、CDS1 / CDS2 信号の立ち下がりに対してどれだけ時間マージンを持っているかを計算・確認するためのツールです。

Excel 設定ファイルからクロック、CDS、電源ネットのタイミング条件を読み込み、PyQtGraph によるタイミング図として表示します。各電源ネットの DCDC スイッチングエッジと CDS1 / CDS2 の立ち下がりエッジとの距離を ns 単位で確認できます。

実行方法:

```bat
uv run python main.py
```

起動時の設定読み込み:

- 起動時に `timing_config_debug.xlsx` が存在する場合は、そのファイルを読み込みます。
- `timing_config_debug.xlsx` が存在しない場合は、空のプロットで起動します。
- 任意の `.xlsx` ファイルは、ウィンドウへドラッグ＆ドロップすることで読み込めます。

設定 Excel:

`config` シートを使用し、`parameter` と `value` の 2 列で設定します。

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
| power_net_duty_percent_0_min | 17.5 |
| power_net_duty_percent_1_min | 21.25 |
| power_net_duty_percent_2_min | 25.0 |
| power_net_duty_percent_3_min | 28.75 |
| power_net_duty_percent_4_min | 32.5 |
| power_net_duty_percent_5_min | 36.25 |
| power_net_duty_percent_6_min |  |
| power_net_duty_percent_7_min |  |
| power_net_duty_percent_0_max | 35.0 |
| power_net_duty_percent_1_max | 42.5 |
| power_net_duty_percent_2_max | 50.0 |
| power_net_duty_percent_3_max | 57.5 |
| power_net_duty_percent_4_max | 65.0 |
| power_net_duty_percent_5_max | 72.5 |
| power_net_duty_percent_6_max |  |
| power_net_duty_percent_7_max |  |

現在のタイミング条件:

- メインの横軸は us です。
- 信号名、ゲート周期、CDS タイミング、分周比は Excel から読み込みます。
- 表示範囲は 0 us から `gate_period_us` までです。
- PL_DCDC_CLK1 は 175 MHz を分周したクロックで、デューティ比は 50% です。
- `pl_dcdc_clk_delay_ns` は PL_DCDC_CLK1 の初期遅延量を ns 単位で指定します。
- `power_net_delay_ns_*` は PL_DCDC_CLK1 から各電源ネットまでの遅延量を ns 単位で指定します。
- `power_net_duty_percent_*_min` / `power_net_duty_percent_*_max` は各電源ネット波形のデューティ比範囲を指定します。値は `0 < min <= max <= 100` です。
- 電源ネット名が空欄、または遅延量 / デューティ比が未設定・不正な場合、その電源ネットはプロットされません。
- PL_DCDC_CLK1 の遅延量は、サイドパネルから ns 単位で編集できます。
- 各電源ネットについて、CDS1 / CDS2 の立ち下がりエッジに最も近い立ち上がり / 立ち下がりエッジまでの距離を ns 単位で表示します。SW↓ は duty 範囲を 0.1% 刻みでサンプリングし、中央のマージンプロットに取り得る縦範囲を表示します。
- タイミング波形は duty min 側を表示します。
- 最大 8 本の電源ネット信号を読み込めます。
- 微調整遅延のメモ: 20 ns および 250 ns
