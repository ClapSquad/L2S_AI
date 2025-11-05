import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score

def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def convert_heatmap_to_labels(heatmap, threshold=0.5, num_points=1000):
    """heatmap을 threshold 기준으로 binary label 시퀀스로 변환"""
    t_values = [p['t'] for p in heatmap]
    min_t, max_t = min(t_values), max(t_values)
    times = np.linspace(min_t, max_t, num=num_points)
    labels = np.zeros_like(times)
    intervals = []
    start = None
    for point in heatmap:
        t, s = point['t'], point['s']
        if s >= threshold and start is None:
            start = t
        elif s < threshold and start is not None:
            intervals.append((start, t))
            start = None
    if start is not None:
        intervals.append((start, heatmap[-1]['t']))

    for (s, e) in intervals:
        labels[(times >= s) & (times <= e)] = 1
    return times, labels

def prediction_to_scores(times, intervals):
    """예측 구간을 score 시퀀스로 변환"""
    scores = np.zeros_like(times)
    for (s, e) in intervals:
        scores[(times >= s) & (times <= e)] = 1
    return scores

def evaluate_map(heatmap_path, result_path, pred_type="pred1", threshold=0.5):
    """prediction 파일과 heatmap GT를 비교하여 mAP 계산"""
    heatmap_data = {item['id']: item['h'] for item in load_jsonl(heatmap_path)}
    preds = load_jsonl(result_path)

    if pred_type == "pred1":  # summarized_results.jsonl
        pred_data = {item['id']: item['result']['timestamps'] for item in preds}
    else:  # predictions.jsonl
        pred_data = {item['video_name'].replace(".mp4", ""): [(p['start'], p['end']) for p in item['highlights']] for item in preds}

    ap_scores = []

    for vid, heatmap in heatmap_data.items():
        if vid not in pred_data:
            continue

        times, gt_labels = convert_heatmap_to_labels(heatmap, threshold)
        pred_scores = prediction_to_scores(times, pred_data[vid])

        # AP 계산
        ap = average_precision_score(gt_labels, pred_scores)
        ap_scores.append(ap)

    return np.mean(ap_scores) if ap_scores else 0

# 실행
if __name__ == "__main__":
    heatmap_path = "heatmap_dataset.jsonl"
    pred1_path = "summarized_results.jsonl"
    pred2_path = "predictions.jsonl"

    map1 = evaluate_map(heatmap_path, pred1_path, pred_type="pred1")
    map2 = evaluate_map(heatmap_path, pred2_path, pred_type="pred2")

    print(f"Prediction 1 mAP: {map1:.4f}")
    print(f"Prediction 2 mAP: {map2:.4f}")

    # 시각화
    models = ['Prediction 1', 'Prediction 2']
    maps = [map1, map2]

    plt.figure(figsize=(6, 4))
    plt.bar(models, maps)
    plt.ylabel("Mean Average Precision (mAP)")
    plt.title("mAP Comparison between Prediction 1 & 2")
    plt.ylim(0, 1)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for i, v in enumerate(maps):
        plt.text(i, v + 0.02, f"{v:.3f}", ha='center')
    plt.show()
