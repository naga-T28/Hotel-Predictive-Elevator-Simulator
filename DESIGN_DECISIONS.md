# 設計決定の根拠（requirements.md 23章）

対象論文: Zhang, J., Tsiligkaridis, A., Taguchi, H., Raghunathan, A., Nikovski,
D. N. *Transformer Networks for Predictive Group Elevator Control*.
MERL TR2022-100 / European Control Conference (ECC) 2022.
[arXiv:2208.08948](https://arxiv.org/abs/2208.08948)

関連文献: Nikovski, D., Brand, M. *Marginalizing Out Future Passengers in
Group Elevator Control*（対象論文中で "Nikovski and Brand [3]" として引用され
ている、到着率から導出した半マルコフ連鎖でロビー階の待ち時間を推定する手法）。

以下、`requirements.md` 23章の各項目について、対象論文から読み取れる事実と、
本プロジェクト独自の判断を分けて記載する。

## 1. エレベーターの加減速をどの程度詳細に再現するか

**決定**: 簡略式（起動時間＋階数差×秒/階＋停止時間）のまま。加速度・最高速度・
減速度は初期実装では再現しない。

対象論文は乗客到着予測とディスパッチ意思決定（PGES: Predictive Group Elevator
Scheduler）が主題であり、エレベーターの走行そのものは商用シミュレータ
**Elevate**（Fig. 2 の構成図で "Continuations of Current Arrival Stream" を
渡す先として示されている）にブラックボックスとして委譲している。論文中に加減速
モデルの記述は一切ない。したがって、群管理アルゴリズムと予測精度の効果検証と
いう研究目的に対して、物理的走行モデルの精度を上げても得られる知見は増えない。
`requirements.md` 5.3 も将来バージョンでの対応としており、本判断と整合する。

## 2. Destination Dispatchを前提とするか

**決定**: 前提とする（実装済み）。

論文 II 節: *"We use a group control algorithm that uses information from a
destination dispatch (DD) input panel that every passenger uses to register
their destination floor."* と明記されている。

## 3. 通常の上下ボタン方式も初期実装へ含めるか

**決定**: 含めない。

同じ段落で *"The algorithm can easily be applied to the more common case of
using only up/down hall-call panels, too, if the algorithm makes an
assumption about the likely destination floor."* と述べているが、論文の実験は
すべてDDで実施されている。初期リリースは論文追試を優先するためDD一本化とする。

## 4. 団体客を分割乗車可能とするか

**決定**: 許可する（`passengers.allow_group_split: true` を既定値とする）。

対象論文には団体客の概念が存在しない（個人単位のPoisson到着のみ）。ホテル固有拡張
として本プロジェクト側で独自に決定する必要がある項目。ホテルの送迎バス・宴会需要
は数人〜十数人規模の団体が多く、全員一括乗車を要求すると乗り残し率が過大評価さ
れるため、定員超過時は先着順に乗車可能な人数だけ乗せ、残りは（再割当を実装しな
い制約と整合させ）乗り残しとして扱う。

## 5. 同一階の複数呼び出しをどの単位で統合するか

**決定**: 統合しない。乗客単位のHallCallのまま個別管理する。

DD方式では乗客ごとに目的階を個別登録するため、呼び出しという概念自体が本質的に
乗客単位である。論文の実験規模（8階・3号機、中程度到着率453.6人/時）でも呼び出し
統合による計算量削減の必要性は論文中に記述がない。本シミュレーターも同規模であり、
統合を省略しても性能要件（15.4節）を満たすため、実装を単純に保つ。

## 6. 停止順序をSchedulerが決定するか、号機内部ロジックが決定するか

**決定**: 号機内部ロジック（SCAN方式）が決定する。Schedulerは「どの号機に割り
当てるか」のみを決定する。

論文のPGESが決定するのは *"which car to assign to pick up a newly arrived
passenger"* のレベルであり、各号機内の停止順序最適化（SCAN/LOOK等）には言及が
ない。商用Elevateの号機内ロジックに委ねている。本実装も `ElevatorCar.add_stop`
によるSCAN順を号機の自律ロジックとし、Schedulerの責務を号機選択に限定すること
で論文と同じ抽象度に揃えている。

## 7. 未来シナリオの最大生成数

**決定**: 既定は単一継続（`number_of_continuations: 1`）。設定により最大4継続
まで拡張可能とする。

論文 II-B-3 "Generation of Continuations": 目的階の多峰性が高い場合は複数
continuationをサンプリングして平均化するが、*"when the multinomial
distribution over continuations is significantly skewed towards one
destination... a simpler computational procedure can be followed to produce
a single most-likely continuation"* と述べ、実際の実験（III節）は単一継続
（PPGE閾値δによる採否判定）で行われている。本実装の `PredictiveScheduler` も
単一継続を既定とし、`requirements.md` 9.9/9.10 で複数シナリオの構造だけ残す。

## 8. 前方シミュレーションの時間範囲

**決定**: 既定120秒（`optimization_horizon_seconds`）。予測ホライズン（論文の
T=10秒）とは独立したパラメータとする。

論文の予測ホライズンT=10秒は「将来乗客をどこまで先まで予測に含めるか」を規定
するものであり、前方シミュレーション自体（仮想的に号機の走行を進めてAWTを評価
する範囲）とは別の概念である。`requirements.md` 10.4 のRolling Horizon例
（`forward_simulation_horizon_seconds: 120`）を踏襲した。

## 9. ホテルイベントの予定誤差分布

**決定**: 正規分布 N(0, spread_seconds)。実験Eでは標準偏差を「誤差なし/
±1分/±3分/±5分」と変化させる。

ホテル固有需要は対象論文のスコープ外（本プロジェクト独自拡張）。多数の個人の
行動開始タイミングが重なる群集流動は中心極限定理的に正規分布で近似するのが
一般的であり、`requirements.md` 6.3 の `spread_seconds` パラメータとも整合する。

## 10. 空運転距離を階数差または実距離のどちらで評価するか

**決定**: 階数差（フロア単位）で評価する。

`requirements.md` 5.3 の移動時間モデル自体が「階数差×1階あたりの移動時間」と
いう階数差ベースの簡略モデルであり、階高（メートル換算の根拠）を扱っていない。
評価指標の単位を移動時間モデルと一致させることで、空運転距離・移動時間・停止
回数を同じ基盤（階数）で比較可能にする。

## 11. エネルギー消費量を評価対象へ含めるか

**決定**: 含めない。

対象論文もAverage Waiting Time (AWT) のみを評価指標としており、エネルギーへの
言及はない。`requirements.md` 2.2 も「エネルギー消費量の厳密な物理計算」を明示
的にスコープ外としている。移動距離・空運転距離が代理指標として機能する。

## 12. 実ホテルデータを利用できるか

**決定**: 利用しない。集計済み統計（客室稼働率、チェックアウト予定人数、朝食
予約人数等）のみを入力とし、個人単位の実データは扱わない。

`requirements.md` 15.7 のプライバシー要件（宿泊者氏名・予約者ID等を保存しない）
と2.2「個人を識別する宿泊者データの利用」除外に整合。対象論文も実在建物の実測
データではなく、SimTreadによる合成軌跡データのみを使用しており、本プロジェクト
も合成データ生成に留めることが研究再現性の観点からも適切である。
