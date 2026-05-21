# Timing Calculation Notes

このアプリの最終目的は、PL_DCDC_CLK1の遅延をパラメータとして、CDS1/CDS2の立ち下がりから3.3V_DIGの立ち上がり/立ち下がりまでの時間を計算し、その時間余裕が最大となるPL_DCDC_CLK1遅延を求めること。

## 見直すべき点

### 1. PL_DCDC_CLK1遅延を3.3V_DIGに反映する

現在の実装では、PL_DCDC_CLK1の遅延入力はPL_DCDC_CLK1の描画には反映されるが、3.3V_DIGのエッジ時刻には反映されていない。

最終目的から見ると、3.3V_DIGの位相はPL_DCDC_CLK1遅延に従属するべき。

想定する形:

```text
PL_DCDC_CLK1 start = PL_DCDC_CLK1 delay
3.3V_DIG start = PL_DCDC_CLK1 delay + 3.3V_DIG internal delay
```

3.3V_DIG internal delay は現在の固定値 20 ns に相当する可能性がある。

### 2. 最大化する評価値を定義する

現在の表示は、CDS1/CDS2の立ち下がりから最も近い3.3V_DIG立ち上がり/立ち下がりまでの差分を出している。

最適なPL_DCDC_CLK1遅延を求めるには、評価関数を明確にする必要がある。

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

最適遅延探索を入れるなら、タイミング計算をUIから独立した関数に切り出すべき。

想定する構造:

```text
timing_model(pl_delay_ns, divider, cds1_fall_us, cds2_fall_us)
  -> 3.3V_DIG edge times
  -> deltas from CDS falling edges
  -> score

find_best_pl_delay(...)
  -> delay candidatesを走査
  -> score最大のdelayを返す
```

draw() は計算結果を受け取って描画と右側表示を更新するだけにする。

## 優先順位

1. 3.3V_DIGの開始時刻をPL_DCDC_CLK1遅延に連動させる
2. 最大化する評価値を `min(abs(...))` ベースで定義する
3. 計算ロジックを描画から切り出す
4. PL_DCDC_CLK1 delayを走査し、score最大の遅延を表示する
