# 要件定義書：ホテル向け予測型エレベーター群管理シミュレーター

> **Status**: Draft
> **最終更新**: 2026-07-22
> **実装言語**: Python
> **対象論文**: Zhang et al., *Transformer Networks for Predictive Group Elevator Control*
> **関連文献**: Nikovski and Brand, *Marginalizing Out Future Passengers in Group Elevator Control*

---

## 1. プロジェクト概要

### 1.1 プロジェクト名

Hotel Predictive Elevator Simulator
以下、本システムを「シミュレーター」と呼ぶ。

### 1.2 目的

本プロジェクトの目的は、複数台のエレベーターが設置されたホテルを対象として、乗客の将来到着情報を利用する予測型群管理制御の効果をPython上で検証できるシミュレーターを構築することである。

シミュレーターでは、従来の事後対応型群管理と、将来需要を考慮する予測型群管理を同一条件で実行し、平均待ち時間、長時間待機、乗り残し、停止回数、空運転距離などを比較する。

最初の段階では論文の実験条件に近い下りピーク交通を再現し、その後、チェックアウト、朝食、宴会終了、団体客到着など、ホテル固有の交通パターンを追加する。

### 1.3 背景

対象論文では、将来エレベーターホールへ到着する可能性のある乗客について、エレベーターへ向かう確率と到着までの残り時間を予測し、その予測情報を群管理へ入力している。

呼び出しが発生した際には、各号機へ仮に呼び出しを割り当て、現在の乗客と予測された将来乗客を含む運行を前方シミュレーションする。その結果、期待平均待ち時間が最も小さくなる号機を実際の担当号機として選択する。

論文の実験では、8階建て、3号機、予測時間10秒、エレベーターへ向かう確率の閾値0.2という条件が使用されている。中程度の到着率では、非予測型制御の平均待ち時間18.1秒に対し、予測型制御では15.3秒という結果が報告されている。

### 1.4 成功の定義

本プロジェクトは、以下の状態を満たした場合に成功とする。

1. 複数階・複数号機・複数乗客を扱う離散事象シミュレーションを実行できる。
2. 非予測型制御と予測型制御を同一の乗客データで比較できる。
3. 乗客の待ち時間、乗車時間、乗り残し、停止回数、空運転距離を記録できる。
4. 乱数シードを固定した場合、同一の実験結果を再現できる。
5. 論文の条件に近い8階・3号機の下りピーク実験を実行できる。
6. ホテル固有の予定情報を利用した需要生成を実行できる。
7. 実験結果をCSV、JSONおよびグラフとして出力できる。
8. 予測精度を変更したときの運行性能への影響を評価できる。

---

## 2. システムの対象範囲

### 2.1 対象とする機能

本システムでは、以下を実装対象とする。

* 乗客到着の生成
* 乗客の出発階と目的階の生成
* ホテルイベントに基づく需要集中の生成
* エレベーター号機の移動
* ドア開閉
* 乗降処理
* 定員管理
* ホール呼び出し管理
* 号機割当
* 停止階順序の管理
* 空き号機の待機位置変更
* 将来乗客の予測
* 予測結果を用いた前方シミュレーション
* 複数制御方式の比較
* 評価指標の集計
* 実験結果の保存と可視化

### 2.2 対象外とする機能

初期バージョンでは、以下は対象外とする。

* 実際のエレベーター制御盤との接続
* モーターやブレーキの物理制御
* 火災時管制や地震時管制
* 故障診断
* 建築基準法上の安全検証
* 実映像を使用した人物追跡
* 個人を識別する宿泊者データの利用
* エネルギー消費量の厳密な物理計算
* SimTreadおよびElevateの完全再実装

### 2.3 再現実験上の制約

対象論文では、人流軌跡の生成にSimTread、エレベーター運行シミュレーションにElevateが使用されている。

本プロジェクトでは、これらをPythonで独自実装するため、論文と完全に同じ平均待ち時間を再現することは必須要件としない。

論文の数値は妥当性確認の参考値として扱い、以下の傾向が再現されることを重視する。

* 完全な将来情報を持つ制御が最も良い結果となる。
* 適切な予測情報を使用した制御は非予測型制御より良い結果となる。
* 交通量が少ないほど事前配置の効果が大きくなる。
* 交通量が増えて全号機が常時稼働すると、予測による改善率が小さくなる。

---

## 3. 想定利用者

### 3.1 研究者・学生

エレベーター群管理、需要予測、最適化、スマートビルディングを研究する学生および研究者が、制御方式を比較するために使用する。

### 3.2 開発者

新しい号機割当アルゴリズム、需要予測モデル、最適化目的関数を実装し、既存方式と比較するために使用する。

### 3.3 ホテル事業者・設備担当者

ホテルの運営予定を利用した場合に、エレベーターの待ち時間や混雑がどの程度改善する可能性があるかを確認するために使用する。

---

## 4. シミュレーションの基本方式

### 4.1 時間管理方式

シミュレーションには、離散事象シミュレーションを採用する。

システム内では、以下のイベントが発生する。

* 乗客の生成
* 乗客のホール到着
* ホール呼び出しの登録
* 号機割当
* エレベーターの移動開始
* エレベーターの階到着
* ドア開放
* 乗客の降車
* 乗客の乗車
* ドア閉鎖
* 次の停止階への移動
* 予測情報の更新
* ホテルイベントの開始または終了

実装には `SimPy` を使用することを推奨する。ただし、独自のイベントキューによる実装も許容する。

### 4.2 時間単位

内部の時間単位は秒とする。

移動時間、ドア開閉時間、乗降時間、乗客到着時刻、予測時間について、整数または浮動小数点数の秒で管理する。

### 4.3 シミュレーション実行時間

1回の実験について、以下を設定可能とする。

* ウォームアップ時間
* 評価対象時間
* クールダウン時間

初期値は以下とする。

```yaml
simulation:
  warmup_seconds: 300
  duration_seconds: 3600
  cooldown_seconds: 300
```

ウォームアップ期間のデータは評価指標へ含めない。

---

## 5. シミュレーション対象モデル

## 5.1 建物モデル

建物は、複数のフロアから構成される。

各フロアには、以下の属性を持たせる。

| 属性                        | 内容                     |
| ------------------------- | ---------------------- |
| `floor_id`                | フロア番号                  |
| `floor_type`              | ロビー、客室、レストラン、宴会場、大浴場など |
| `room_count`              | 客室数                    |
| `occupancy_rate`          | 稼働率                    |
| `is_elevator_serviceable` | エレベーター停止可否             |
| `population`              | 推定滞在人数                 |

フロア数は設定ファイルから変更可能とする。

論文再現モードでは8階建てとし、1階をロビー、2階から8階を一般フロアとして扱う。

### 5.2 エレベーターモデル

各号機は、以下の状態を保持する。

| 属性                | 内容           |
| ----------------- | ------------ |
| `car_id`          | 号機ID         |
| `current_floor`   | 現在階          |
| `position`        | 階間を含む現在位置    |
| `direction`       | 上昇、下降、停止     |
| `state`           | 現在の動作状態      |
| `capacity_people` | 最大乗車人数       |
| `capacity_weight` | 最大積載重量       |
| `current_load`    | 現在の乗車人数または重量 |
| `passengers`      | 乗車中の乗客       |
| `assigned_calls`  | 割り当て済み呼び出し   |
| `stop_queue`      | 停止予定階        |
| `total_distance`  | 総移動距離        |
| `empty_distance`  | 空運転距離        |
| `stop_count`      | 停止回数         |

号機の状態は、以下のいずれかとする。

```text
IDLE
MOVING_UP
MOVING_DOWN
DOOR_OPENING
DOOR_OPEN
BOARDING
ALIGHTING
DOOR_CLOSING
```

### 5.3 エレベーター移動時間

初期バージョンでは、エレベーターの移動時間を次式で簡略化する。

```text
移動時間
= 起動時間
+ 階数差 × 1階当たりの移動時間
+ 停止時間
```

将来バージョンでは、加速度、最高速度、減速度、階高を考慮する。

設定例を以下に示す。

```yaml
elevators:
  count: 3
  capacity_people: 15
  seconds_per_floor: 2.5
  start_delay_seconds: 1.0
  door_open_seconds: 1.5
  door_close_seconds: 1.5
  boarding_seconds_per_person: 0.7
  alighting_seconds_per_person: 0.6
```

### 5.4 乗客モデル

乗客は、以下の属性を持つ。

| 属性                  | 内容            |
| ------------------- | ------------- |
| `passenger_id`      | 乗客ID          |
| `generated_at`      | システム上で生成された時刻 |
| `hall_arrival_time` | エレベーターホール到着時刻 |
| `origin_floor`      | 出発階           |
| `destination_floor` | 目的階           |
| `direction`         | 上りまたは下り       |
| `group_id`          | 団体ID          |
| `group_size`        | 団体人数          |
| `luggage_factor`    | 荷物による占有量      |
| `call_time`         | 呼び出し登録時刻      |
| `assigned_car_id`   | 割り当て号機        |
| `board_time`        | 乗車時刻          |
| `arrival_time`      | 目的階到着時刻       |
| `status`            | 現在状態          |

乗客状態は、以下のいずれかとする。

```text
GENERATED
WALKING_TO_ELEVATOR
WAITING
ASSIGNED
ONBOARD
ARRIVED
LEFT_BEHIND
ABANDONED
```

### 5.5 団体客と荷物

団体客については、複数人を一つのグループとして生成する。

グループを分割して乗車可能とするかは設定可能とする。

```yaml
passengers:
  allow_group_split: true
```

荷物を持つ乗客は、通常乗客より多くの定員を消費するものとして扱う。

例えば、通常乗客の占有量を1.0、スーツケースを持つ乗客を1.5として設定する。

---

## 6. 需要生成要件

### 6.1 基本到着過程

通常時の乗客到着は、Poisson過程を基本とする。

各時間帯、出発階、目的階の組合せについて、到着率を設定できるようにする。

```yaml
traffic:
  default_process: poisson
  intervals:
    - start: "07:00:00"
      end: "09:00:00"
      rate_per_hour: 300
      pattern: breakfast
    - start: "09:00:00"
      end: "11:00:00"
      rate_per_hour: 500
      pattern: checkout
```

### 6.2 交通パターン

最低限、以下の交通パターンを実装する。

#### Up-peak

ロビー階から複数の上層階へ向かう需要が集中する。

#### Down-peak

複数の上層階からロビー階へ向かう需要が集中する。

#### Inter-floor

ロビー以外のフロア間で移動する。

#### Two-way traffic

上り需要と下り需要が同時に発生する。

#### Burst traffic

イベント終了などにより、短時間に大量の乗客が発生する。

### 6.3 ホテル固有イベント

以下のイベントを設定できるようにする。

| イベント    | 想定される需要           |
| ------- | ----------------- |
| チェックイン  | ロビーから客室階への上り      |
| チェックアウト | 客室階からロビーへの下り      |
| 朝食開始    | 客室階からレストラン階       |
| 朝食終了    | レストラン階から客室階またはロビー |
| 宴会開始    | ロビーまたは客室階から宴会場    |
| 宴会終了    | 宴会場からロビーまたは客室階    |
| 大浴場利用   | 客室階と大浴場階の双方向移動    |
| 送迎バス到着  | ロビーから複数客室階への上り    |
| 送迎バス出発  | 複数客室階からロビーへの下り    |

ホテルイベントは以下の形式で入力する。

```yaml
hotel_events:
  - event_id: banquet_001
    event_type: banquet_end
    time: "20:30:00"
    source_floor: 3
    destination_distribution:
      1: 0.60
      6: 0.10
      7: 0.15
      8: 0.15
    expected_people: 120
    spread_seconds: 300
```

### 6.4 論文再現モード

論文再現モードでは、以下を初期条件とする。

* フロア数：8
* ロビー階：1階
* 一般フロア：2階から8階
* 号機数：3
* 交通パターン：午後の下りピーク
* エレベーター利用者の目的階：1階
* 予測時間：10秒
* 予測確率閾値：0.2
* 中程度の総到着率：453.6人/時
* 各到着率について50回実行可能

論文では、1フロア当たり64.8人/時を7フロアへ適用し、総到着率453.6人/時としている。また、到着率ごとの結果を50回の実験で平均化している。

---

## 7. ホール呼び出し要件

### 7.1 呼び出し方式

以下の2種類を実装可能な構造とする。

#### 通常ホールボタン方式

乗客は上りまたは下りのみを登録する。

#### Destination Dispatch方式

乗客はホールで目的階を登録する。

初期バージョンでは、論文に合わせてDestination Dispatch方式を使用する。

### 7.2 即時割当

呼び出し登録時に担当号機を決定する。

一度割り当てられた号機は、原則として変更しない。

設定によって再割当を許可できる設計とするが、初期バージョンでは再割当を実装しない。

### 7.3 同一呼び出しの統合

同一階、同一方向、一定時間内に発生した呼び出しについて、以下を設定可能とする。

* 個別の乗客として管理する
* 一つのホール呼び出しとして統合する
* Destination Dispatchの目的階単位で統合する

---

## 8. 制御アルゴリズム要件

最低限、以下の制御方式を実装する。

### 8.1 Myopic Scheduler

将来の乗客情報を使用せず、現在発生している呼び出しと既存の停止予定のみを用いる。

新しい呼び出しを各号機へ仮割当し、現在存在する乗客のみを対象とした予測待ち時間が最小になる号機を選択する。

本方式を主要なベースラインとする。

### 8.2 Nearest Car Scheduler

現在位置、進行方向および停止予定から、呼び出し地点へ最も早く到着すると推定される号機を選択する。

実装確認用の単純なベースラインとして使用する。

### 8.3 Parking Scheduler

空き号機を、設定された待機階へ移動させる。

以下の方式を選択可能とする。

* 全号機をロビーへ配置
* 各号機を固定階へ配置
* 低層、中層、高層へ分散
* 現在の推定需要が多い階へ配置

### 8.4 Prescient Scheduler

将来発生する乗客の到着時刻、出発階、目的階を完全に知っているものとして運行を決定する。

現実には実現不可能であるが、予測型制御の性能上限を測定するために使用する。

### 8.5 Predictive Group Elevator Scheduler

予測された将来乗客を利用して号機を割り当てる。

新しい呼び出しが発生した場合、以下の処理を行う。

1. 各号機へ新しい呼び出しを仮割当する。
2. 予測時間内に到着する将来乗客を取得する。
3. 現在の乗客と将来乗客を含めて、各号機の運行を前方シミュレーションする。
4. 各仮割当について平均待ち時間または目的関数を計算する。
5. 期待コストが最小の号機へ呼び出しを割り当てる。

概念的な処理は以下とする。

```python
def assign_call(call, simulation_state, predictor):
    best_car_id = None
    best_cost = float("inf")

    future_scenarios = predictor.generate_future_scenarios(
        state=simulation_state,
        horizon_seconds=config.prediction_horizon,
    )

    for car in simulation_state.cars:
        scenario_costs = []

        for future_scenario in future_scenarios:
            copied_state = simulation_state.clone()
            copied_state.assign(call, car.car_id)

            result = forward_simulate(
                state=copied_state,
                future_passengers=future_scenario,
                horizon_seconds=config.optimization_horizon,
            )

            scenario_costs.append(calculate_cost(result))

        expected_cost = mean(scenario_costs)

        if expected_cost < best_cost:
            best_cost = expected_cost
            best_car_id = car.car_id

    return best_car_id
```

### 8.6 ホテル情報利用型Scheduler

ホテルの予定情報から推定したフロア別需要を予測型Schedulerへ入力する。

例えば、チェックアウト予定者が多いフロアについて、チェックアウト時間直前から将来下り乗客の発生確率を増加させる。

本方式では、個人の移動軌跡が存在しない場合でも、以下の情報から将来乗客を生成できるようにする。

* フロア別在室人数
* チェックアウト予定人数
* 朝食予約人数
* 宴会参加人数
* 団体客人数
* イベント開始・終了時刻
* ホールの現在人数
* 過去の時間帯別到着率

---

## 9. 予測モジュール要件

### 9.1 共通インターフェース

予測器は、以下の共通インターフェースを実装する。

```python
class PassengerPredictor(Protocol):
    def predict_future_passengers(
        self,
        current_time: float,
        horizon_seconds: float,
        simulation_state: SimulationState,
    ) -> list[PredictedPassenger]:
        ...
```

`PredictedPassenger` は、最低限以下を保持する。

```python
@dataclass
class PredictedPassenger:
    predicted_arrival_time: float
    origin_floor: int
    destination_floor: int | None
    probability: float
    expected_group_size: float = 1.0
```

### 9.2 Oracle Predictor

シミュレーター内部の実際の将来乗客をそのまま返す。

Prescient Schedulerの評価に使用する。

### 9.3 No Prediction

将来乗客を一切返さない。

Myopic Schedulerに使用する。

### 9.4 Aggregate Poisson Predictor

過去または設定済みの到着率に基づき、予測区間内の将来乗客を生成する。

初期の予測型制御の検証に使用する。

### 9.5 Noisy Predictor

真の将来乗客に対して、以下の誤差を人工的に加える。

* 検出漏れ
* 誤検出
* 到着時刻誤差
* 出発階誤差
* 目的階誤差
* 人数誤差

以下を設定可能とする。

```yaml
prediction_error:
  recall: 0.80
  precision: 0.90
  arrival_time_std_seconds: 2.0
  destination_accuracy: 0.95
```

本予測器により、予測精度と運行性能の関係を分析する。

### 9.6 軌跡ベースPredictor

論文に近い再現を行う場合、各フロア上を移動する人物の2次元軌跡を生成する。

人物の軌跡は、グリッドIDの系列として保持する。

```python
trajectory = [
    (grid_id_1, timestamp_1),
    (grid_id_2, timestamp_2),
    ...
]
```

論文では、位置を50×50のグリッドへ離散化している。

軌跡ベースPredictorは、以下の2段階で構成する。

1. エレベーターへ向かう確率の予測
2. エレベーターホールへ到着するまでの残り時間の予測

### 9.7 Transformerによる目的地予測

Transformerモデルは、途中まで観測された位置系列を入力し、人物がエレベーターへ向かっている確率を出力する。

```python
probability = destination_model.predict_probability(
    partial_trajectory
)
```

確率が設定された閾値以上の場合のみ、将来乗客として採用する。

```text
probability >= PPGE threshold
```

初期閾値は論文と同じ0.2とするが、検証データから変更可能とする。

### 9.8 到着残り時間予測

エレベーターへ向かうと予測された人物について、線形回帰を使用して到着までの残り時間を予測する。

初期モデルは以下とする。

```text
remaining_time = β0 + β1 × x + β2 × y
```

必要に応じて、歩行速度を追加する。

```text
remaining_time = β0 + β1 × x + β2 × y + β3 × walking_speed
```

論文では、エレベーターへ向かう軌跡から線形回帰を構築し、残り時間予測のRMSEとして1.29秒を報告している。

### 9.9 単一未来シナリオ

予測確率が十分高い場合には、確率が閾値以上の乗客のみを将来到着列へ追加する。

```python
if probability >= threshold:
    if predicted_remaining_time <= prediction_horizon:
        continuation.append(predicted_passenger)
```

### 9.10 複数未来シナリオ

予測に大きな不確実性がある場合、確率分布から複数の未来到着列をサンプリングする。

各号機の評価値は、複数シナリオの平均値とする。

```text
期待コスト
= 各未来シナリオにおけるコストの平均
```

論文でも、複数の将来到着列を生成し、それぞれの平均待ち時間を平均することでMonte Carlo期待値を計算している。

---

## 10. 最適化要件

### 10.1 基本目的関数

初期バージョンでは、平均待ち時間を最小化する。

```text
J = Average Waiting Time
```

### 10.2 拡張目的関数

ホテル向け評価では、以下の複合目的関数を使用可能とする。

[
J =
\alpha W_{\mathrm{avg}}
+\beta W_{95}
+\gamma T_{\mathrm{travel}}
+\delta R_{\mathrm{left}}
+\epsilon N_{\mathrm{stop}}
+\zeta D_{\mathrm{empty}}
+\eta C_{\mathrm{crowding}}
]

各変数は以下を表す。

| 変数                      | 内容             |
| ----------------------- | -------------- |
| (W_{\mathrm{avg}})      | 平均待ち時間         |
| (W_{95})                | 待ち時間の95パーセンタイル |
| (T_{\mathrm{travel}})   | 平均乗車時間         |
| (R_{\mathrm{left}})     | 乗り残し率          |
| (N_{\mathrm{stop}})     | 停止回数           |
| (D_{\mathrm{empty}})    | 空運転距離          |
| (C_{\mathrm{crowding}}) | 混雑度            |

### 10.3 重み設定

目的関数の重みは設定ファイルから変更可能とする。

```yaml
objective:
  average_waiting_time: 1.0
  p95_waiting_time: 0.5
  travel_time: 0.2
  left_behind_rate: 2.0
  stop_count: 0.05
  empty_distance: 0.05
  crowding: 0.2
```

### 10.4 Rolling Horizon

ホテル情報利用型制御では、一定周期で将来需要を再予測する。

```yaml
optimization:
  prediction_horizon_seconds: 60
  replanning_interval_seconds: 5
  forward_simulation_horizon_seconds: 120
```

ただし、論文再現モードでは予測時間を10秒とする。

---

## 11. 評価指標

### 11.1 乗客単位の指標

各乗客について、以下を記録する。

```text
waiting_time = board_time - hall_arrival_time
ride_time = arrival_time - board_time
total_service_time = arrival_time - hall_arrival_time
```

### 11.2 運行性能指標

以下を集計する。

* 平均待ち時間
* 待ち時間中央値
* 待ち時間95パーセンタイル
* 最大待ち時間
* 平均乗車時間
* 平均総所要時間
* 30秒以上待機した乗客の割合
* 60秒以上待機した乗客の割合
* 乗り残し人数
* 乗り残し率
* 輸送完了人数
* 1時間当たり輸送人数

### 11.3 号機単位の指標

* 総移動距離
* 空運転距離
* 乗客輸送中の移動距離
* 停止回数
* ドア開閉回数
* 平均積載率
* 最大積載率
* 稼働時間
* 待機時間
* 号機ごとの輸送人数

### 11.4 予測性能指標

* Precision
* Recall
* F1-score
* 誤検出数
* 検出漏れ数
* 到着時刻予測MAE
* 到着時刻予測RMSE
* 目的階予測精度
* 予測確率のCalibration
* 予測が実運行へ採用された割合

### 11.5 計算性能指標

* 1回の号機割当に要した時間
* 最大割当計算時間
* シミュレーション全体の実行時間
* 前方シミュレーション回数
* 未来シナリオ生成数

---

## 12. 実験要件

### 12.1 実験A：論文条件に近い再現

以下の方式を比較する。

1. Prescient Scheduler
2. Predictive Scheduler
3. 単純予測型Scheduler
4. Myopic Scheduler

主要評価指標は平均待ち時間とする。

参考目標として、論文では以下の結果が報告されている。

| 制御方式                                  | 平均待ち時間 |
| ------------------------------------- | -----: |
| Prescient Scheduler                   |  13.2秒 |
| Transformer Predictive Scheduler      |  15.3秒 |
| Closest-distance Predictive Scheduler |  17.4秒 |
| Myopic Scheduler                      |  18.1秒 |

これらの数値との完全一致は求めないが、制御方式間の性能順序が概ね一致することを確認する。

### 12.2 実験B：到着率による影響

乗客到着率を段階的に変更する。

各到着率について複数の乱数シードを使用し、平均値と標準偏差を算出する。

出力するグラフは以下とする。

* 到着率と平均待ち時間
* 到着率と平均待ち時間削減率
* 到着率と95パーセンタイル待ち時間
* 到着率と乗り残し率
* 到着率と空運転距離

### 12.3 実験C：チェックアウト需要

複数の客室階からロビーへ下り需要が集中する状況を再現する。

比較対象は以下とする。

* 非予測型制御
* ロビー待機方式
* 客室階への事前配置方式
* ホテル情報利用型予測制御

比較は同一の乗客到着系列（共通乱数シード）を用いた対応あり実験とし、各方式を
原則50回実行する。ロビー待機または客室階への事前配置を併用する場合は、待機方式
だけを変更した対照条件を設け、需要予測による効果と事前配置による効果を分離する。

### 12.4 実験D：朝食時間帯

客室階からレストラン階への移動と、レストラン階から客室階またはロビーへの移動を再現する。

単純な下りピークではない、複数方向交通における有効性を評価する。

非予測型制御、同一の待機方式を使用した非予測型制御、ホテル情報利用型予測制御を
同一需要系列で比較する。

### 12.5 実験E：宴会終了

一つのフロアから短時間に大量の乗客が発生する。

イベント終了時刻の予測誤差を以下の条件で比較する。

```text
誤差なし
±1分
±3分
±5分
```

誤差は実際の乗客発生時刻には加えず、予測器へ渡すイベント予定時刻だけに加える。
これにより、交通需要そのものの変化と予測誤差の影響を混同しない。

### 12.6 実験F：団体客と荷物

団体客人数と荷物量を変化させ、実質輸送容量が低下した場合の性能を評価する。

### 12.7 実験G：予測誤差

以下のパラメータを変更する。

* Precision
* Recall
* 到着時刻誤差
* 目的階誤差
* 予測時間
* 予測確率閾値

予測精度がどの程度まで低下すると、非予測型制御より性能が悪化するかを確認する。

### 12.8 統計的比較と再現性

制御方式間の比較では、すべての方式に同じ乱数シード集合を使用する。主要評価指標は
平均待ち時間とし、方式ごとの平均値・標準偏差・95%信頼区間に加え、基準方式との
シードごとの対応差、その95%信頼区間、改善率を出力する。副次評価指標として、
95パーセンタイル待ち時間、30秒超待ち率、乗り残し率、総サービス時間、空運転距離、
停止回数を報告する。ホテルシナリオ間は需要量と継続時間が異なるため直接比較せず、
各シナリオ内で制御方式を比較する。

ホテル情報利用型予測の有効性を主張するための最小比較条件を以下とする。

1. 将来情報を使用しない基準制御
2. 基準制御と事前配置のみを組み合わせた制御
3. 2と同じ事前配置を使用するホテル情報利用型予測制御
4. 完全な将来情報を利用する上限性能の参考制御

実験設定、乱数シード、ソフトウェアのバージョン、および集計前の各反復結果を保存する。

---

## 13. 入出力要件

### 13.1 設定ファイル

設定はYAML形式を基本とする。

```yaml
experiment:
  name: paper_reproduction
  random_seed: 42
  repetitions: 50

building:
  floors: 8
  lobby_floor: 1

elevators:
  count: 3
  capacity_people: 15
  seconds_per_floor: 2.5
  door_open_seconds: 1.5
  door_close_seconds: 1.5

traffic:
  pattern: down_peak
  total_arrival_rate_per_hour: 453.6

scheduler:
  type: predictive
  immediate_assignment: true

prediction:
  type: noisy_oracle
  horizon_seconds: 10
  probability_threshold: 0.2
  number_of_continuations: 1

simulation:
  duration_seconds: 3600
```

### 13.2 CSV入力

将来、実データまたは外部生成データを読み込めるようにする。

乗客入力CSVは以下の形式とする。

```csv
passenger_id,hall_arrival_time,origin_floor,destination_floor,group_size,luggage_factor
P0001,12.4,8,1,1,1.0
P0002,14.8,6,1,3,1.2
```

ホテルイベント入力CSVは以下の形式とする。

```csv
event_id,event_type,start_time,end_time,floor,expected_people
E001,breakfast,25200,28800,2,80
E002,banquet,64800,73800,3,120
```

### 13.3 出力ファイル

実験ごとに以下を出力する。

```text
outputs/
└── experiment_name/
    ├── config.yaml
    ├── summary.json
    ├── passenger_metrics.csv
    ├── elevator_metrics.csv
    ├── event_log.csv
    ├── assignment_log.csv
    ├── prediction_log.csv
    └── figures/
        ├── waiting_time_distribution.png
        ├── arrival_rate_vs_awt.png
        ├── elevator_position_timeline.png
        └── occupancy_timeline.png
```

### 13.4 イベントログ

最低限、以下をイベントログへ記録する。

```text
timestamp
event_type
passenger_id
car_id
floor
direction
load
assigned_calls
stop_queue
```

---

## 14. 可視化要件

以下の可視化を実装する。

### 14.1 待ち時間分布

制御方式ごとの待ち時間を箱ひげ図またはヒストグラムで表示する。

### 14.2 エレベーター運行軌跡

横軸を時間、縦軸をフロアとして、各号機の移動を表示する。

### 14.3 乗客到着数

時間帯別・フロア別の乗客到着数を表示する。

### 14.4 積載率

各号機の積載率を時系列で表示する。

### 14.5 制御方式比較

制御方式ごとに以下を棒グラフで比較する。

* 平均待ち時間
* 95パーセンタイル待ち時間
* 乗り残し率
* 空運転距離
* 停止回数

### 14.6 アニメーション

必須ではないが、将来的にはエレベーターと待機乗客の状態をアニメーション表示できる構造とする。

---

## 15. 非機能要件

### 15.1 実行環境

* Python 3.11以上
* Windows、macOS、Linuxで実行可能
* CPUのみで基本シミュレーションを実行可能
* Transformer学習時のみGPUを任意利用

### 15.2 推奨ライブラリ

```text
simpy
numpy
pandas
scipy
scikit-learn
matplotlib
pydantic
pyyaml
pytest
torch
```

`torch` はTransformerを実装する段階で導入する。

### 15.3 再現性

全ての乱数生成器について、乱数シードを設定する。

対象は以下とする。

* Python標準の `random`
* NumPy
* PyTorch
* 乗客生成
* 未来シナリオ生成

### 15.4 性能

初期目標として、一般的なノートパソコン上で以下を満たす。

* 8階・3号機・1時間分の基本シミュレーションを1分以内で実行する。
* 非予測型の号機割当を1件当たり100ミリ秒以内で処理する。
* 予測型割当を1件当たり1秒以内で処理する。
* 50回の実験を並列実行できる。

Transformerの学習時間は、この性能要件に含めない。

### 15.5 拡張性

以下を個別に交換できる設計とする。

* 乗客生成器
* 需要予測器
* 号機割当アルゴリズム
* 停止順序決定アルゴリズム
* 目的関数
* エレベーター物理モデル
* 評価指標

### 15.6 テスト可能性

シミュレーション内部の主要処理について、外部状態に依存しない単体テストを作成する。

### 15.7 プライバシー

ホテルデータを使用する場合、以下を直接保存しない。

* 宿泊者氏名
* 予約者ID
* 電話番号
* メールアドレス
* 客室番号と個人の対応情報
* 個人単位の長期間の移動履歴

フロア別人数や時間帯別人数へ集計したデータを使用する。

---

## 16. データモデル

### 16.1 Passenger

```python
@dataclass
class Passenger:
    passenger_id: str
    hall_arrival_time: float
    origin_floor: int
    destination_floor: int
    group_size: int = 1
    luggage_factor: float = 1.0

    assigned_car_id: str | None = None
    call_time: float | None = None
    board_time: float | None = None
    destination_arrival_time: float | None = None
```

### 16.2 ElevatorCar

```python
@dataclass
class ElevatorCar:
    car_id: str
    current_position: float
    direction: int
    state: str
    capacity: float
    current_load: float

    passengers: list[Passenger]
    assigned_calls: list[str]
    stop_queue: list[int]
```

### 16.3 HallCall

```python
@dataclass
class HallCall:
    call_id: str
    registered_at: float
    origin_floor: int
    destination_floor: int | None
    direction: int
    passenger_ids: list[str]
    assigned_car_id: str | None = None
```

### 16.4 Prediction

```python
@dataclass
class Prediction:
    prediction_id: str
    created_at: float
    predicted_arrival_time: float
    origin_floor: int
    destination_floor: int | None
    probability: float
    true_passenger_id: str | None = None
```

### 16.5 HotelEvent

```python
@dataclass
class HotelEvent:
    event_id: str
    event_type: str
    start_time: float
    end_time: float
    source_floors: list[int]
    destination_distribution: dict[int, float]
    expected_people: int
```

---

## 17. システム構成

```text
hotel-elevator-simulator/
├── README.md
├── pyproject.toml
├── configs/
│   ├── paper_reproduction.yaml
│   ├── hotel_checkout.yaml
│   ├── hotel_breakfast.yaml
│   └── hotel_banquet.yaml
├── src/
│   └── elevator_sim/
│       ├── domain/
│       │   ├── passenger.py
│       │   ├── elevator.py
│       │   ├── hall_call.py
│       │   ├── building.py
│       │   └── hotel_event.py
│       ├── simulation/
│       │   ├── engine.py
│       │   ├── event_queue.py
│       │   ├── forward_simulator.py
│       │   └── state.py
│       ├── traffic/
│       │   ├── base.py
│       │   ├── poisson.py
│       │   ├── hotel_schedule.py
│       │   └── trajectory.py
│       ├── schedulers/
│       │   ├── base.py
│       │   ├── nearest_car.py
│       │   ├── myopic.py
│       │   ├── parking.py
│       │   ├── prescient.py
│       │   └── predictive.py
│       ├── predictors/
│       │   ├── base.py
│       │   ├── no_prediction.py
│       │   ├── oracle.py
│       │   ├── noisy_oracle.py
│       │   ├── poisson.py
│       │   ├── linear_rtd.py
│       │   └── transformer.py
│       ├── metrics/
│       │   ├── passenger_metrics.py
│       │   ├── elevator_metrics.py
│       │   └── prediction_metrics.py
│       ├── experiments/
│       │   ├── runner.py
│       │   └── comparison.py
│       ├── visualization/
│       │   ├── waiting_time.py
│       │   ├── timeline.py
│       │   └── traffic.py
│       └── cli.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scenarios/
└── outputs/
```

---

## 18. コマンドライン要件

### 18.1 単一実験

```bash
python -m elevator_sim run \
  --config configs/paper_reproduction.yaml
```

### 18.2 制御方式比較

```bash
python -m elevator_sim compare \
  --config configs/paper_reproduction.yaml \
  --schedulers myopic,predictive,prescient
```

### 18.3 複数乱数シード実験

```bash
python -m elevator_sim experiment \
  --config configs/paper_reproduction.yaml \
  --runs 50 \
  --parallel 4
```

### 18.4 結果可視化

```bash
python -m elevator_sim plot \
  --input outputs/paper_reproduction
```

---

## 19. テスト要件

### 19.1 単体テスト

以下をテストする。

* 階間移動時間の計算
* 定員判定
* 乗車処理
* 降車処理
* 待ち時間計算
* 停止階追加
* 停止階並べ替え
* 呼び出し割当
* 予測閾値判定
* Poisson到着生成
* 目的関数計算

### 19.2 不変条件テスト

シミュレーション中、以下が常に成立しなければならない。

* 号機の積載量が最大容量を超えない。
* 乗客が同時に複数の号機へ乗車しない。
* 乗客の乗車時刻がホール到着時刻より前にならない。
* 目的階到着時刻が乗車時刻より前にならない。
* エレベーターが建物の範囲外へ移動しない。
* 同一乗客が複数回輸送完了にならない。
* 完了済み呼び出しが停止予定へ残らない。

### 19.3 統合テスト

以下の小規模シナリオを用意する。

#### 1号機・2階・1乗客

乗客が確実に目的階へ到着することを確認する。

#### 1号機・満員状態

定員を超える乗客が乗り残しになることを確認する。

#### 2号機・同一距離

タイブレーク規則に従って号機が選択されることを確認する。

#### 予測乗客あり

予測型Schedulerが将来乗客を考慮した号機を選択することを確認する。

### 19.4 回帰テスト

固定シードの代表シナリオについて、主要指標が許容範囲を超えて変化していないことを確認する。

---

## 20. 受け入れ基準

### 20.1 シミュレーション基盤

* 設定された階数と号機数で実行できる。
* 指定時間までシミュレーションが停止せず完了する。
* 全乗客の状態遷移を追跡できる。
* 定員制約が適用される。
* 待ち時間と乗車時間が正しく計算される。

### 20.2 制御方式

* Myopic Schedulerを実行できる。
* Prescient Schedulerを実行できる。
* Predictive Schedulerを実行できる。
* 同じ乗客到着列で各方式を比較できる。
* 将来情報を無効化したPredictive SchedulerがMyopic Schedulerと同等の挙動になる。

### 20.3 実験

* 8階・3号機の下りピーク実験を実行できる。
* 到着率を変更した複数実験を実行できる。
* 50回分の実験結果を集計できる。
* 平均値と標準偏差を出力できる。
* 制御方式ごとの待ち時間削減率を計算できる。

### 20.4 出力

* 乗客単位のCSVを出力できる。
* 号機単位のCSVを出力できる。
* 実験概要をJSONで出力できる。
* 待ち時間比較グラフを出力できる。
* 号機位置の時系列グラフを出力できる。

### 20.5 再現性

同一設定、同一乱数シード、同一バージョンで実行した場合、主要な集計結果が一致する。

---

## 21. 開発フェーズ

### Phase 1：基本シミュレーター

以下を実装する。

* 建物モデル
* 乗客モデル
* エレベーターモデル
* Poisson到着
* 移動、乗車、降車
* Nearest Car Scheduler
* Myopic Scheduler
* 基本評価指標
* CSV出力

この段階では機械学習を使用しない。

### Phase 2：予測型群管理

以下を実装する。

* Oracle Predictor
* Noisy Predictor
* Prescient Scheduler
* Predictive Scheduler
* 前方シミュレーション
* 複数未来シナリオ
* 論文条件に近い比較実験

この段階で、予測情報が運行へ与える効果を検証できる状態にする。

### Phase 3：軌跡予測

以下を実装する。

* 2次元フロアモデル
* 人物軌跡生成
* グリッド離散化
* 線形回帰による残り時間予測
* Transformerによる目的地予測
* PPGE閾値処理

### Phase 4：ホテル固有需要

以下を実装する。

* 客室稼働率
* チェックアウト予定
* 朝食予定
* 宴会予定
* 団体客
* 送迎バス
* 荷物による容量低下
* フロア別需要予測
* Rolling Horizon Optimization

### Phase 5：高度な最適化

必要に応じて以下を検討する。

* 混合整数計画
* メタヒューリスティクス
* モンテカルロ木探索
* 強化学習
* ゾーニング最適化
* エネルギー最適化

---

## 22. 初期実装における優先順位

最初からTransformerを実装するのではなく、以下の順序で開発する。

1. 乗客とエレベーターが正しく動くシミュレーター
2. 非予測型Scheduler
3. 真の将来情報を使用するPrescient Scheduler
4. 真の情報に人工的な誤差を加えたPredictive Scheduler
5. ホテルイベントに基づく将来需要予測
6. 軌跡データと線形回帰
7. Transformerによる目的地予測

この順序にすることで、予測モデルが未完成でも、群管理アルゴリズムとシミュレーション基盤の検証を進められる。

---

## 23. 未決定事項（決定済み）

以下は、対象論文 Zhang et al., *Transformer Networks for Predictive Group
Elevator Control* (MERL TR2022-100, ECC 2022, arXiv:2208.08948) および
Nikovski and Brand, *Marginalizing Out Future Passengers in Group Elevator
Control* を参考に決定した。詳細な根拠は `DESIGN_DECISIONS.md` を参照。

| # | 項目 | 決定 |
|---|------|------|
| 1 | エレベーターの加減速の詳細度 | 簡略式（起動時間＋階数差×秒/階＋停止時間）のまま。対象論文も商用シミュレータElevateを物理演算のブラックボックスとして使うのみで、GEC/予測アルゴリズムの検証が主眼であるため詳細な物理再現は不要と判断。 |
| 2 | Destination Dispatchを前提とするか | 前提とする。対象論文が明示的にDD（destination-dispatch）方式を採用。 |
| 3 | 上下ボタン方式を初期実装へ含めるか | 含めない。対象論文も「上下ボタン方式にも拡張可能」と述べるに留め、実験はDDのみで実施。 |
| 4 | 団体客の分割乗車 | 許可する（`allow_group_split: true`）。対象論文に団体客の概念はなく、ホテル固有拡張として独自決定。定員超過時は先着順に乗車可能な人数のみ乗せ、残りは乗り残しとする。 |
| 5 | 同一階呼び出しの統合単位 | 統合しない（乗客単位のHallCallのまま個別管理）。DD方式では呼び出し自体が本質的に乗客単位であり、3号機・8階規模では統合による計算量削減の必要がない。 |
| 6 | 停止順序の決定主体 | 号機内部ロジック（SCAN方式）。対象論文のPGESは「どの号機に割り当てるか」のみを決定しており、号機内の停止順序最適化には言及していない。 |
| 7 | 未来シナリオの最大生成数 | 既定は単一継続（`number_of_continuations: 1`）。対象論文が「多峰性が高い場合のみ複数continuationを生成し、それ以外は単一の最尤continuationで十分」としているため、単一継続をデフォルトとし、設定で最大4継続まで拡張可能とする。 |
| 8 | 前方シミュレーションの時間範囲 | 既定120秒（`optimization_horizon_seconds`）。予測ホライズン（対象論文のT=10秒）とは独立したパラメータとし、要件書10.4のRolling Horizon例を踏襲。 |
| 9 | ホテルイベントの予定誤差分布 | 正規分布 N(0, spread_seconds)。対象論文に相当する記述はなく、群集流動の到着時刻ばらつきの一般的モデル化慣行に従う。 |
| 10 | 空運転距離の評価単位 | 階数差（フロア単位）。移動時間モデル自体が階数差ベースの簡略モデルであるため、指標の単位を統一する。 |
| 11 | エネルギー消費量を評価対象に含めるか | 含めない。対象論文もAWTのみを評価指標としており、要件書2.2で明示的にスコープ外としている。 |
| 12 | 実ホテルデータの利用 | 利用しない。集計済み統計（客室稼働率、チェックアウト予定人数等）のみを入力とし、個人単位の実データは扱わない。要件書15.7のプライバシー要件に整合。対象論文もSimTreadによる合成データのみを使用している。 |

---

## 24. 初期リリースの最低要件

初期リリースでは、以下のみを必須とする。

* 8階建て
* 3号機
* 1階ロビー
* 2階から8階から1階への下り交通
* Poisson到着
* 定員制約
* Myopic Scheduler
* Prescient Scheduler
* Noisy Predictorを利用したPredictive Scheduler
* 平均待ち時間
* 95パーセンタイル待ち時間
* 乗り残し率
* 空運転距離
* 50回の反復実験
* CSVおよびグラフ出力

Transformerおよび2次元人物軌跡は、初期リリース後の追加機能とする。
