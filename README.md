# Hotel Predictive Elevator Simulator

ホテル内で発生する時間帯別・階別の移動需要を再現し、複数のエレベーター群管理方式を比較するための離散事象シミュレーターです。

SimPyを用いて、乗客の到着、ホール呼び出し、号機割当、乗降、階間移動、待機位置制御をシミュレーションします。

同一の乗客到着列に対して複数の制御方式を実行できるため、号機割当方式や需要予測方式による違いを比較できます。

## 主な機能

* 8階建てなど任意の建物条件の設定
* 複数台のエレベーターの運行
* 乗客到着とホール呼び出しの生成
* Poisson到着過程による基礎交通の生成
* チェックアウト、朝食、宴会終了などのホテル需要生成
* 団体客と荷物による容量消費
* 複数の号機割当方式
* 将来需要を利用した予測型割当
* 空き号機の待機位置制御
* 歩行軌跡を利用した需要予測
* 複数乱数シードによる反復実験
* 制御方式間の対応比較
* CSV、JSON、グラフの出力

本リポジトリはシミュレーション用のプロトタイプです。実際のエレベーター制御装置への接続や、安全制御の実装を目的としたものではありません。

---

## 目次

* [シミュレーションの概要](#シミュレーションの概要)
* [実装内容](#実装内容)
* [セットアップ](#セットアップ)
* [基本的な使い方](#基本的な使い方)
* [制御方式](#制御方式)
* [需要生成方式](#需要生成方式)
* [ホテル需要シナリオ](#ホテル需要シナリオ)
* [設定ファイル](#設定ファイル)
* [比較実験](#比較実験)
* [感度分析](#感度分析)
* [出力ファイル](#出力ファイル)
* [テスト](#テスト)
* [ディレクトリ構成](#ディレクトリ構成)
* [既知の制約](#既知の制約)

---

## シミュレーションの概要

ホテルでは、時間帯や館内イベントによってエレベーター需要が変化します。

代表的な需要には、以下があります。

* 客室階からロビーへ集中するチェックアウト需要
* 客室階とレストラン階の間を移動する朝食需要
* 宴会場からロビーや客室階へ移動する宴会終了需要
* 通常時に断続的に発生する基礎交通
* 団体客や荷物を持つ利用者による容量消費

本シミュレーターでは、これらの需要を仮想的に生成し、エレベーターの待ち時間や運行量を記録します。

主な評価指標は以下のとおりです。

* 平均待ち時間
* 95パーセンタイル待ち時間
* 最大待ち時間
* 一定時間を超えた待ちの発生率
* 乗り残し率
* 乗車時間
* 空運転距離
* 総走行距離
* 停止回数
* 輸送件数

---

## 実装内容

### 基本シミュレーター

* 建物モデル
* 乗客モデル
* 乗客グループモデル
* エレベーターモデル
* ホール呼び出し
* 乗車・降車処理
* 階間移動
* ドア開閉時間
* 定員制約
* 荷物係数
* イベントログ
* 乗客・号機ごとの指標集計

### 号機割当

以下の号機割当方式を実装しています。

* Nearest Car
* Myopic
* Prescient
* Predictive

新しいホール呼び出しが発生すると、各方式に応じて担当号機を決定します。

Predictive Schedulerでは、予測された将来乗客を前方シミュレーションに加え、推定待ち時間に基づいて担当号機を選択します。

### 需要予測

以下の予測器を実装しています。

* No Prediction
* Oracle
* Noisy Oracle
* Poisson
* Linear Remaining-Time Predictor
* Transformer Predictor
* Trajectory-Based Predictor
* Hotel-Informed Predictor

### 歩行軌跡シミュレーション

* 2次元フロアモデル
* グリッド離散化
* 歩行速度の設定
* エレベーターへ向かう軌跡
* エレベーターへ向かわないデコイ軌跡
* 線形回帰による到着時間予測
* Transformerによる到着確率予測

歩行モデルは簡易的な独自実装です。実際のホテル内の歩行や、市販の避難・歩行シミュレーターの挙動を完全に再現するものではありません。

### ホテル固有需要

`HotelEvent`を使用して、ホテル内のイベントに応じた需要を生成できます。

対応するイベント例は以下です。

* チェックアウト
* 朝食
* 宴会終了
* 団体移動
* 任意の館内イベント

イベントごとに、次の項目を設定できます。

* イベント時刻
* 発生時間帯
* 発生人数
* 出発階
* 目的階
* 乗客グループの人数
* 荷物係数
* 到着時刻の分散

### 待機位置制御

空き号機の待機位置を定期的に更新できます。

対応する方式は以下です。

* 全号機をロビーへ移動
* 号機ごとの固定階
* 低層・中層・高層へのゾーン分散
* 予測需要に基づく配置

現在の待機位置制御は、空き号機の配置のみを変更します。割当済み呼び出しや停止順序全体の再計算は行いません。

---

## セットアップ

### 必要環境

* Python 3.11以上
* pip
* venvまたは同等の仮想環境

歩行軌跡のTransformer予測ではPyTorchを使用します。

### インストール

```bash
git clone https://github.com/naga-T28/Hotel-Predictive-Elevator-Simulator.git
cd Hotel-Predictive-Elevator-Simulator

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

Windows PowerShellでは、次のコマンドで仮想環境を有効化します。

```powershell
.venv\Scripts\Activate.ps1
```

---

## 基本的な使い方

### 単一シミュレーション

```bash
python -m elevator_sim run \
  --config configs/paper_reproduction.yaml
```

### チェックアウト需要

```bash
python -m elevator_sim run \
  --config configs/hotel_checkout.yaml
```

### 朝食需要

```bash
python -m elevator_sim run \
  --config configs/hotel_breakfast.yaml
```

### 宴会終了需要

```bash
python -m elevator_sim run \
  --config configs/hotel_banquet.yaml
```

### 歩行軌跡を利用した予測

```bash
python -m elevator_sim run \
  --config configs/trajectory_prediction.yaml
```

### 複数乱数シードによる反復実験

```bash
python -m elevator_sim experiment \
  --config configs/hotel_checkout.yaml \
  --runs 50 \
  --parallel 4
```

`--runs`には実行回数、`--parallel`には並列実行数を指定します。

### グラフの再生成

```bash
python -m elevator_sim plot \
  --input outputs/hotel_checkout
```

---

## 制御方式

### Nearest Car

呼び出し階との距離や進行方向に基づいて、比較的近い号機へ呼び出しを割り当てます。

### Myopic

現在の号機状態と登録済み呼び出しを用いて、現在発生している呼び出しの割当を決定します。

将来の乗客需要は利用しません。

### Predictive

現在の呼び出しに加えて、予測された将来乗客を前方シミュレーションへ含めます。

各号機へ呼び出しを仮割当し、推定される待ち時間を比較して担当号機を選択します。

### Prescient

シミュレーション上で生成済みの将来到着情報を使用する比較用方式です。

ただし、現在の逐次割当と近似的な前方シミュレーションに従って動作するため、数学的に最適な上限を保証するものではありません。

### Parking

空き号機を指定された階へ移動します。

Parkingは号機割当方式とは独立して有効化できます。

---

## 需要生成方式

### Poisson到着

通常時の乗客到着を、Poisson到着過程として生成します。

到着率、出発階、目的階分布などを設定ファイルから変更できます。

### 下りピーク

複数の上層階から低層階またはロビーへ向かう需要を生成します。

### 上りピーク

ロビーや低層階から上層階へ向かう需要を生成します。

### 歩行軌跡

2次元空間上で仮想利用者を移動させ、エレベーターホールへの到着を生成します。

### ホテルイベント

ホテルイベントの時刻と人数に基づいて、特定の時間帯に需要を集中させます。

基礎交通とホテルイベント需要は同時に生成できます。

---

## ホテル需要シナリオ

### チェックアウト

客室階からロビーへ向かう下り需要を生成します。

主な設定項目は以下です。

* チェックアウト予定時刻
* 発生人数
* 客室階の分布
* グループ人数
* 荷物係数
* 到着時刻の標準偏差
* 基礎交通の到着率

### 朝食

客室階とレストラン階の間に双方向需要を生成します。

朝食会場へ向かう需要と、食事終了後に客室階へ戻る需要を設定できます。

### 宴会終了

宴会場からロビー、客室階、その他の館内施設へ向かう需要を生成します。

イベント終了時刻に対する予測誤差も設定できます。

---

## 設定ファイル

実験条件はYAMLファイルで指定します。

### 主な設定項目

| キー                    | 設定値の例                                                                 | 内容         |
| --------------------- | --------------------------------------------------------------------- | ---------- |
| `traffic.pattern`     | `down_peak`、`up_peak`、`trajectory`、`hotel`                            | 需要生成方式     |
| `scheduler.type`      | `nearest_car`、`myopic`、`prescient`、`predictive`                       | 号機割当方式     |
| `prediction.type`     | `no_prediction`、`oracle`、`noisy_oracle`、`trajectory`、`hotel_informed` | 需要予測方式     |
| `parking.enabled`     | `true`、`false`                                                        | 待機位置制御の有効化 |
| `parking.strategy`    | `all_to_lobby`、`fixed_per_car`、`zoned`、`demand_weighted`              | 待機位置の決定方式  |
| `hotel_events`        | `HotelEvent`のリスト                                                      | ホテルイベントの設定 |
| `simulation.duration` | 秒数                                                                    | シミュレーション時間 |
| `building.floors`     | 整数                                                                    | 建物の階数      |
| `elevators.count`     | 整数                                                                    | エレベーター台数   |
| `elevators.capacity`  | 数値                                                                    | 1台当たりの容量   |
| `random_seed`         | 整数                                                                    | 乱数シード      |

### 歩行軌跡設定

`prediction.type: trajectory`を使用する場合は、`trajectory`セクションで以下を設定します。

* グリッド解像度
* フロアサイズ
* 歩行速度
* 軌跡数
* デコイ軌跡の割合
* 学習エポック数
* Transformerのパラメータ

学習用の軌跡と評価用の軌跡には、異なる派生乱数シードを使用します。

---

## 比較実験

`compare`コマンドを使用すると、同じ乗客到着列に対して複数の制御方式を実行できます。

```bash
python -m elevator_sim compare \
  --config configs/validation/hotel_checkout_trio.yaml \
  --schedulers myopic,predictive,prescient \
  --baseline myopic \
  --runs 50 \
  --parallel 4 \
  --output outputs/hotel_checkout_comparison
```

各乱数シードについて同一の乗客需要を生成し、制御方式だけを変更します。

これにより、乗客需要のばらつきを抑えた対応比較が可能です。

### 別設定のBaselineを使用する場合

Parkingを使用しない条件など、別の設定ファイルをBaselineとして指定できます。

```bash
python -m elevator_sim compare \
  --config configs/validation/hotel_checkout_trio.yaml \
  --schedulers myopic,predictive,prescient \
  --baseline myopic \
  --baseline-config configs/validation/hotel_checkout_baseline.yaml \
  --baseline-label baseline \
  --runs 50 \
  --parallel 4 \
  --output outputs/hotel_checkout_validation
```

### 比較条件の例

| 条件                  | 将来需要       | 待機位置制御 |
| ------------------- | ---------- | ------ |
| Baseline            | 使用しない      | 使用しない  |
| Parking only        | 使用しない      | 使用する   |
| Hotel predictive    | ホテル予定から推定  | 使用する   |
| Prescient reference | 実際の将来到着を参照 | 使用する   |

---

## 感度分析

### イベント予定時刻の誤差

`prediction_time_offset_seconds`を使用すると、実際の需要発生時刻を変更せず、予測器が参照する予定時刻だけをずらせます。

```yaml
prediction_time_offset_seconds: 60.0
```

対応する設定例は以下です。

```text
configs/validation/hotel_banquet_trio_offset_0.yaml
configs/validation/hotel_banquet_trio_offset_plus60.yaml
configs/validation/hotel_banquet_trio_offset_minus60.yaml
configs/validation/hotel_banquet_trio_offset_plus180.yaml
configs/validation/hotel_banquet_trio_offset_minus180.yaml
configs/validation/hotel_banquet_trio_offset_plus300.yaml
configs/validation/hotel_banquet_trio_offset_minus300.yaml
```

### 荷物係数

```text
configs/validation/hotel_checkout_trio_luggage_1.0.yaml
configs/validation/hotel_checkout_trio_luggage_2.0.yaml
```

標準設定では、荷物係数1.5を使用します。

```text
configs/validation/hotel_checkout_trio.yaml
```

### 予測ホライズン

```text
configs/validation/hotel_checkout_trio_horizon_10.yaml
configs/validation/hotel_checkout_trio_horizon_20.yaml
configs/validation/hotel_checkout_trio_horizon_40.yaml
```

標準設定では、60秒の予測ホライズンを使用します。

---

## 出力ファイル

単一実行の結果は、原則として以下へ保存されます。

```text
outputs/<experiment_name>/
```

### 単一実行

```text
outputs/<experiment_name>/
├── summary.json
├── passenger_metrics.csv
├── elevator_metrics.csv
├── event_log.csv
├── assignment_log.csv
└── figures/
    └── *.png
```

### 比較実験

```text
outputs/<comparison_name>/
├── baseline/
├── myopic/
├── predictive/
├── prescient/
├── comparison_summary.csv
├── comparison_summary.json
├── paired_comparisons.csv
├── paired_comparisons.json
└── paired_comparisons_vs_baseline.csv
```

各方式の全反復ログは、以下へ保存されます。

```text
<condition>/runs/seed_*/
```

### 主な出力内容

#### `summary.json`

実験条件と主要な評価指標を保存します。

#### `passenger_metrics.csv`

乗客または乗客グループごとの指標を保存します。

* 到着時刻
* 出発階
* 目的階
* 待ち時間
* 乗車時間
* 乗り残し
* 担当号機

#### `elevator_metrics.csv`

号機ごとの運行指標を保存します。

* 総走行距離
* 空運転距離
* 停止回数
* 輸送件数
* 稼働時間

#### `event_log.csv`

シミュレーション中に発生したイベントを時系列で保存します。

#### `assignment_log.csv`

ホール呼び出しと担当号機の割当結果を保存します。

#### `comparison_summary.csv`

各制御方式について、複数乱数シードの平均値、標準偏差、信頼区間を保存します。

#### `paired_comparisons.csv`

同じ乱数シードにおける、基準方式と候補方式の指標差を保存します。

---

## テスト

すべてのテストは次のコマンドで実行できます。

```bash
pytest
```

主に以下を検証しています。

* 号機の移動
* 停止順序
* 乗車・降車処理
* 定員判定
* 待ち時間計算
* Poisson到着過程
* ホテル需要生成
* グリッド離散化
* 歩行軌跡生成
* 線形回帰による到着時間予測
* Transformerによる分類
* 待機位置制御
* 予測情報を無効化した場合の動作
* イベント時刻誤差の注入
* 複数設定間の対応比較
* CSV・JSON出力

テスト件数は開発に伴って変化するため、最新の`pytest`実行結果を確認してください。

---

## ディレクトリ構成

```text
src/elevator_sim/
├── domain/
│   ├── passenger.py
│   ├── elevator.py
│   ├── hall_call.py
│   ├── building.py
│   └── hotel_event.py
├── simulation/
│   ├── engine.py
│   ├── state.py
│   └── forward_simulation.py
├── traffic/
│   ├── poisson.py
│   ├── trajectory.py
│   ├── grid.py
│   └── hotel.py
├── schedulers/
│   ├── nearest_car.py
│   ├── myopic.py
│   ├── prescient.py
│   ├── predictive.py
│   └── parking.py
├── predictors/
│   ├── no_prediction.py
│   ├── oracle.py
│   ├── noisy_oracle.py
│   ├── poisson.py
│   ├── linear_rtd.py
│   ├── transformer.py
│   ├── trajectory_based.py
│   └── hotel_informed.py
├── metrics/
├── experiments/
├── visualization/
├── config.py
└── cli.py
```

---

## 既知の制約

### 乗客モデル

* 団体客は1つの乗客グループレコードとして管理します。
* 定員判定では、グループ人数と荷物係数を考慮します。
* 待ち時間、乗り残し率、輸送件数はグループ単位で集計します。
* 現在の乗降時間は、グループ人数に比例して増加しません。
* 厳密な利用者1人当たりの指標には対応していません。

### エレベーターモデル

* 実機の制御装置とは接続していません。
* モーター、ブレーキ、着床、安全装置、非常時管制は再現していません。
* 階間移動時間やドア時間は簡略化したモデルです。
* 加速度や減速度を含む連続的な物理モデルではありません。

### 号機割当

* 割当済み呼び出しの再割当は実装していません。
* 全号機の停止順序を同時に再最適化する機能はありません。
* Predictive Schedulerは逐次的な号機割当を行います。
* Prescient Schedulerは厳密な最適解を求める方式ではありません。

### 待機位置制御

* 待機位置の再計算は一定周期で実行されます。
* 運行計画全体の再最適化は行いません。
* 呼び出し処理中の号機は、原則として待機位置変更の対象外です。

### 予測モデル

* ホテル情報予測では、イベント予定時刻の誤差を設定できます。
* 予測人数の誤差を独立に与える機能は未実装です。
* 目的階分布の誤差を独立に与える機能は未実装です。
* 歩行軌跡モデルは簡易モデルです。
* 実際のホテルの映像や位置情報は使用していません。

### 評価指標

以下の項目は未実装です。

* エネルギー消費量
* 最大割当計算時間
* 詳細な予測ログ
* 利用者1人単位で重み付けした全指標
* 乗降人数に応じた可変乗降時間

---

## 関連ドキュメント

### [`requirements.md`](requirements.md)

シミュレーターの機能要件、設定項目、実装範囲を記載しています。

### [`EXPERIMENT_VALIDATION_PLAN.md`](EXPERIMENT_VALIDATION_PLAN.md)

制御方式の比較条件、反復実験、評価指標、感度分析の方法を記載しています。

### [`EXPERIMENT_RESULTS_GUIDE.md`](EXPERIMENT_RESULTS_GUIDE.md)

出力ファイル、評価指標、比較結果の確認方法を記載しています。

---

## 再現実行

同じ結果を再現する場合は、以下を固定してください。

* 設定ファイル
* 乱数シード
* Pythonバージョン
* 依存パッケージ
* 実行コマンド
* Gitコミット

例：

```text
Version: v1.0.0
Commit: abcdef1
Python: 3.11
Config: configs/validation/hotel_checkout_trio.yaml
Runs: 50
```

公開済みの結果とコードを対応付ける場合は、Gitタグまたはリリースを作成することを推奨します。
