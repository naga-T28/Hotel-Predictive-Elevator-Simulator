# Hotel Predictive Elevator Simulator

`requirements.md` の要件定義に基づく、ホテル向け予測型エレベーター群管理シミュレーター。
離散事象シミュレーション（SimPy）上で、非予測型・単純近接・完全未来情報・予測型（ノイズ付き
Oracle／軌跡＋Transformer／ホテル情報利用型）・待機位置最適化の各制御方式を、同一の乗客
到着列で比較できる。

対象論文 Zhang et al., *Transformer Networks for Predictive Group Elevator Control*
(MERL TR2022-100, ECC 2022) の追試（8階建て・3号機・下りピーク、予測ホライズン10秒、
PPGE閾値0.2）に加えて、論文にない要素（団体客・荷物・ホテル固有需要）を独自拡張として
実装している。`requirements.md` 23章の未決定事項の決定根拠は `DESIGN_DECISIONS.md` を参照。

本リポジトリは研究用プロトタイプである。現在の予測型制御は、予測乗客を含む前方計算に
基づく逐次号機割当と、独立した定期的な待機位置更新を実装している。論文中の式(1)に示す
多目的最適化、割当済み呼び出しの再割当、停止順序全体の再最適化を完全実装したものではない。
論文用実験の設計と主張可能な範囲は `EXPERIMENT_VALIDATION_PLAN.md` を参照。

対応範囲は Phase 1〜4（`requirements.md` 21章）。Phase 5（高度な最適化・強化学習等）は
「必要に応じて検討する」とされる将来拡張のため未実装。

## Phase別の実装内容

- **Phase 1（基本シミュレーター）**: 建物・乗客・エレベーターモデル、Poisson到着、
  移動/乗車/降車、定員制約、Nearest Car / Myopic Scheduler、CSV出力。
- **Phase 2（予測型群管理）**: Oracle / Noisy Oracle Predictor、Prescient / Predictive
  Scheduler、前方シミュレーション、単一〜複数未来シナリオ、PPGE閾値フィルタ。
- **Phase 3（軌跡予測）**: 2次元フロアモデルと50×50グリッド離散化、SimTread代替の
  独自2D歩行軌跡生成器（エレベーター行き／デコイ）、線形回帰による残り時間予測、
  Transformer（エンコーダ分類器）による「エレベーターへ向かう確率」予測。
- **Phase 4（ホテル固有需要）**: `HotelEvent`（チェックアウト・朝食・宴会終了等）に基づく
  需要生成、ホテル情報利用型Predictor（イベント時刻周辺で発生率を高めるガウス型モデル）、
  Parking Scheduler（ロビー集約／号機別固定階／低中高分散／需要加重）、一定周期での
  待機位置再計算。これは待機位置に対する周期的更新であり、運行計画全体の
  Rolling Horizon Optimizationではない。

## セットアップ

Python 3.11以上が必要。軌跡予測ではPyTorchを使用するため、利用環境に対応した
PyTorchパッケージをインストールする。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 使い方

```bash
# 単一実験（論文再現条件）
python -m elevator_sim run --config configs/paper_reproduction.yaml

# 軌跡＋Transformer予測（Phase 3）
python -m elevator_sim run --config configs/trajectory_prediction.yaml

# ホテル固有需要（Phase 4: チェックアウト／朝食／宴会終了）
python -m elevator_sim run --config configs/hotel_checkout.yaml
python -m elevator_sim run --config configs/hotel_breakfast.yaml
python -m elevator_sim run --config configs/hotel_banquet.yaml

# 制御方式の比較
python -m elevator_sim compare \
  --config configs/paper_reproduction.yaml \
  --schedulers myopic,nearest_car,predictive,prescient \
  --baseline myopic \
  --runs 50 \
  --output outputs/paper_reproduction_validation

# 複数乱数シードでの反復実験（並列実行対応）
python -m elevator_sim experiment \
  --config configs/paper_reproduction.yaml \
  --runs 50 --parallel 4

# 既存の出力ディレクトリからグラフを再生成
python -m elevator_sim plot --input outputs/paper_reproduction
```

単一実験の出力は `outputs/<experiment_name>/` 以下に `summary.json`、
`passenger_metrics.csv`、`elevator_metrics.csv`、`event_log.csv`、
`assignment_log.csv`、`figures/*.png` として書き出される。比較実験では、これらに加えて
`comparison_summary.csv/json`、`paired_comparisons.csv/json`、および各条件の
`runs/seed_*/` に全反復の未集計ログを保存する。

## 設定ファイルの主な切り替え

| キー | 値 | 内容 |
| --- | --- | --- |
| `traffic.pattern` | `down_peak` / `up_peak` / `trajectory` / `hotel` | 需要生成方式 |
| `scheduler.type` | `nearest_car` / `myopic` / `prescient` / `predictive` / `parking` | 号機割当方式 |
| `prediction.type` | `no_prediction` / `oracle` / `noisy_oracle` / `trajectory` / `hotel_informed` | 予測器 |
| `parking.enabled` + `parking.strategy` | `all_to_lobby` / `fixed_per_car` / `zoned` / `demand_weighted` | 待機位置最適化の併用 |
| `hotel_events` | `HotelEvent`のリスト | チェックアウト・朝食・宴会等のイベント需要 |

`prediction.type: trajectory` を使う場合、`trajectory:` セクションでグリッド解像度・
歩行速度・Transformer学習エポック数等を指定する。学習データは実行と同じ乱数シードから
派生した別シードで生成するため、評価対象の軌跡そのもので学習することはない
（論文の学習/テスト分割に対応）。

## 検証実験（`EXPERIMENT_VALIDATION_PLAN.md`対応）

ホテル固有需要（Phase 4）が「待機位置最適化だけの効果」と「ホテル情報予測の効果」を
分離して検証できるよう、`configs/validation/` に4条件比較用のconfigを用意している
（詳細は `EXPERIMENT_VALIDATION_PLAN.md` 参照）。

- **Baseline**: `scheduler.type: myopic` + `parking.enabled: false` + `prediction.type: no_prediction`
  （`*_baseline.yaml`）。
- **Parking only / Hotel predictive / Prescient reference**: 同一の`parking`設定を持つ1つのconfig
  （`*_trio.yaml`）に対し、`compare --schedulers myopic,predictive,prescient`で3条件を同時実行する
  （駐機ロジックは`scheduler.type`と独立に動作するため、`myopic`はParking-only相当になる）。

Baselineとtrioは別YAMLだが`parking.enabled`だけが異なるため、`compare`だけでは1回の実行に
まとめられない。これに対応するため`compare`に`--baseline-config`/`--baseline-label`/`--parallel`
を追加した（`--baseline-config`省略時は既存動作と完全に同一）。

```bash
python -m elevator_sim compare \
  --config configs/validation/hotel_checkout_trio.yaml \
  --schedulers myopic,predictive,prescient \
  --baseline myopic \
  --baseline-config configs/validation/hotel_checkout_baseline.yaml \
  --baseline-label baseline \
  --runs 50 --parallel 4 \
  --output outputs/hotel_checkout_validation
```

出力ディレクトリには4条件分の`baseline/`・`myopic/`・`predictive/`・`prescient/`
（代表run + `runs/seed_*`）に加え、`comparison_summary.csv`（各条件の平均・標準偏差・95%CI）、
`paired_comparisons.csv`（`--baseline`基準、既定はParking-only = H2用）、
`paired_comparisons_vs_<baseline-label>.csv`（真のBaseline基準 = H1用、`--baseline-config`
指定時のみ追加出力）が書き出される。候補方式－基準方式の待ち時間差について、95%信頼区間の
上限が0秒未満なら「今回の条件では待ち時間を短縮した」と判断する
（`EXPERIMENT_VALIDATION_PLAN.md` 6章）。

宴会終了イベントの予測誤差実験（3.3章）用に、`HotelEventConfig`へ
`prediction_time_offset_seconds`（既定0.0）を追加した。実需要生成（`hotel_events`の
`start_time`）はそのまま使い、`HotelInformedPredictor`が参照する予定時刻だけをこの秒数
ずらす。`configs/validation/hotel_banquet_trio_offset_{0,plus60,minus60,plus180,minus180,
plus300,minus300}.yaml`が対応する（`OraclePredictor`/`PrescientScheduler`は`hotel_events`を
参照しないため、この誤差はHotel predictive条件のみに影響する）。

同様に、荷物係数スイープ（`configs/validation/hotel_checkout_trio_luggage_{1.0,2.0}.yaml`、
既存`1.5`は`hotel_checkout_trio.yaml`）と予測時間スイープ
（`hotel_checkout_trio_horizon_{10,20,40}.yaml`、既存`60`は`hotel_checkout_trio.yaml`）も
用意している。

checkoutシナリオのみ4条件×50シードを実行済み（`outputs/hotel_checkout_validation/`）。
Hotel predictiveはParking onlyに対して平均待ち時間を1.17秒（7.80%）短縮し、対応差の
95%信頼区間は−1.31〜−1.03秒だった。ただし、これは設定したチェックアウト需要に限った
シミュレーション結果であり、他シナリオや実ホテルへ一般化できる結果ではない。
チェックアウト需要は宛先が100%ロビーのため、待機中の号機は駐機指示がなくても自然にロビーへ
戻っており、このシナリオでは Parking only と Baseline がほぼ一致する。breakfast・banquetの
オフセット/luggage/horizonスイープはconfigのみ整備済みで、実行は同様のコマンドで行える。

Prescientは完全な将来到着を参照するが、現在の前方計算と逐次割当の近似に従うため、常に他方式を
上回る数学的な上限ではない。実際、checkoutの実行済み結果ではHotel predictiveより平均待ち時間が
長かった。この結果は、将来情報の価値そのものよりも、現在の割当評価と経路近似に改善余地がある
ことを示している。

## テスト

```bash
pytest
```

単体テスト・統合テストでは、号機の停止順序、定員判定、待ち時間計算、Poisson到着、
グリッド離散化、軌跡生成、Transformer/線形回帰の予測精度、ホテル需要生成、待機位置
最適化、将来情報を無効化したPredictiveがMyopicと同等になることの確認、
`prediction_time_offset_seconds`によるホテル情報予測器への予測誤差注入、
`compare --baseline-config`の対応差出力等を検証する。テスト件数は開発に伴い変化するため、
実行時のpytest出力を正とする。

## ディレクトリ構成

```text
src/elevator_sim/
├── domain/            # Passenger, ElevatorCar, HallCall, Building, HotelEvent
├── simulation/         # SimPyエンジン, SimulationState, 前方シミュレーション
├── traffic/            # Poisson到着過程, グリッド離散化, 2D軌跡生成, ホテル需要生成
├── schedulers/          # nearest_car, myopic, prescient, predictive, parking
├── predictors/           # no_prediction, oracle, noisy_oracle, poisson,
│                         # linear_rtd, transformer, trajectory_based, hotel_informed
├── metrics/              # 乗客/号機指標の集計
├── experiments/          # 単発実行・反復実行・比較実行
├── visualization/        # matplotlibによるグラフ出力
├── config.py              # YAML設定スキーマ
└── cli.py                 # run/compare/experiment/plot コマンド
```

## 既知の制約

- `prediction_time_offset_seconds`はイベント時刻誤差を予測側だけに与えられるが、予測人数や
  目的階分布の誤差をホテル情報利用型Predictorへ独立に与える機能は未実装。
- 周期的更新は待機位置の再計算のみを対象とし、既に割り当て済みの呼び出しの再割当や
  停止順序全体の再最適化は実装していない。
- Predictive Schedulerの目的関数は推定平均待ち時間であり、論文の式(1)に示した
  95%待ち時間、混雑度、停止回数、空運転距離を含む多目的関数は未実装。
- Prescient SchedulerはOracle到着情報を使う比較用実装だが、探索空間と経路評価が近似的なため、
  厳密な性能上限を保証しない。
- 要件に記載された `prediction_log.csv`、エネルギー消費量、最大割当計算時間は未出力。
- breakfast、banquet、予測誤差、荷物係数、予測時間の検証configは用意されているが、
  論文用の全条件・50シード実験は未完了。
- 実ホテルデータ・実映像・Elevate/SimTreadとの接続は`requirements.md` 2.2の通り対象外。
