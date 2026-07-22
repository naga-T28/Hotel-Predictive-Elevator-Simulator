# Hotel Predictive Elevator Simulator

`requirements.md` の要件定義に基づく、ホテル向け予測型エレベーター群管理シミュレーター。
離散事象シミュレーション（SimPy）上で、非予測型・単純近接・完全未来情報・予測型（ノイズ付き
Oracle／軌跡＋Transformer／ホテル情報利用型）・待機位置最適化の各制御方式を、同一の乗客
到着列で比較できる。

対象論文 Zhang et al., *Transformer Networks for Predictive Group Elevator Control*
(MERL TR2022-100, ECC 2022) の追試（8階建て・3号機・下りピーク、予測ホライズン10秒、
PPGE閾値0.2）に加えて、論文にない要素（団体客・荷物・ホテル固有需要）を独自拡張として
実装している。`requirements.md` 23章の未決定事項の決定根拠は `DESIGN_DECISIONS.md` を参照。

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
  待機位置再計算（Rolling Horizon）。

## セットアップ

Python 3.11以上が必要（PyTorchを使用するため、Apple SiliconはmacOS 3.9+推奨）。

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
  --schedulers myopic,nearest_car,prescient,predictive \
  --runs 5

# 複数乱数シードでの反復実験（並列実行対応）
python -m elevator_sim experiment \
  --config configs/paper_reproduction.yaml \
  --runs 50 --parallel 4

# 既存の出力ディレクトリからグラフを再生成
python -m elevator_sim plot --input outputs/paper_reproduction
```

出力は `outputs/<experiment_name>/` 以下に `summary.json` / `passenger_metrics.csv` /
`elevator_metrics.csv` / `event_log.csv` / `assignment_log.csv` / `figures/*.png` として書き出される。

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

## テスト

```bash
pytest
```

単体テスト・統合テストで57件（号機の停止順序、定員判定、待ち時間計算、Poisson到着、
グリッド離散化、軌跡生成、Transformer/線形回帰の予測精度、ホテル需要生成、待機位置
最適化、将来情報を無効化したPredictiveがMyopicと同等になることの確認、等）。

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

- 実験E（`requirements.md` 12.5）で想定されるイベント時刻の予測誤差評価は未実装。
  現状は`hotel_events`をホテル情報利用型Predictorがそのまま真値として参照するため、
  予測とホテル運営予定の間に誤差を注入する仕組みはない（別スケジュールを与える拡張で
  対応可能）。
- Rolling Horizonは待機位置の再計算のみを対象とし、既に割り当て済みの呼び出しの
  再割当は`requirements.md` 7.2の方針通り実装していない。
- 実ホテルデータ・実映像・Elevate/SimTreadとの接続は`requirements.md` 2.2の通り対象外。
