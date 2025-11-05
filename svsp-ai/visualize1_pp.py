import json
import numpy as np
import matplotlib.pyplot as plt

def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def convert_heatmap_to_intervals(heatmap, threshold=0.5):
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
    return intervals

def evaluate_prediction(heatmap_data, pred_data, threshold=0.5):
    metrics = {}
    for vid, pred_intervals in pred_data.items():
        if vid not in heatmap_data:
            continue

        gt_intervals = convert_heatmap_to_intervals(heatmap_data[vid], threshold)
        t_values = [p['t'] for p in heatmap_data[vid]]

        tp, fp, fn = 0, 0, 0
        time_points = np.linspace(min(t_values), max(t_values), num=1000)

        for t in time_points:
            gt_label = any(start <= t <= end for start, end in gt_intervals)
            pred_label = any(start <= t <= end for start, end in pred_intervals)
            if gt_label and pred_label:
                tp += 1
            elif not gt_label and pred_label:
                fp += 1
            elif gt_label and not pred_label:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        metrics[vid] = {"precision": precision, "recall": recall, "f1": f1}

    mean_precision = np.mean([m["precision"] for m in metrics.values()]) if metrics else 0
    mean_recall = np.mean([m["recall"] for m in metrics.values()]) if metrics else 0
    mean_f1 = np.mean([m["f1"] for m in metrics.values()]) if metrics else 0

    return mean_precision, mean_recall, mean_f1


def prepare_data(heatmap_path, summarized_path, predictions_path, hd_path):
    heatmap_data = {item['id']: item['h'] for item in load_jsonl(heatmap_path)}

    summarized_data = {
        item['id']: [tuple(ts) for ts in item['result']['timestamps']]
        for item in load_jsonl(summarized_path)
    }

    pred2_raw = load_jsonl(predictions_path)
    predictions_data = {
        item['video_name'].replace('.mp4', ''): [(h['start'], h['end']) for h in item['highlights']]
        for item in pred2_raw
    }

    hd_raw = load_jsonl(hd_path)
    predictions_hd = {
        item['video_name'].replace('.mp4', ''): [(h['start'], h['end']) for h in item['highlights']]
        for item in hd_raw
    }

    return heatmap_data, summarized_data, predictions_data, predictions_hd


def plot_precision_recall_curves(heatmap_path, summarized_path, predictions_path, hd_path):
    heatmap_data, summarized_data, predictions_data, predictions_hd = prepare_data(
        heatmap_path, summarized_path, predictions_path, hd_path
    )

    thresholds = np.linspace(0.1, 0.9, 9)
    pr_llm, rc_llm = [], []
    pr_yo, rc_yo = [], []
    pr_hd, rc_hd = [], []

    for th in thresholds:
        p1, r1, _ = evaluate_prediction(heatmap_data, summarized_data, threshold=th)
        p2, r2, _ = evaluate_prediction(heatmap_data, predictions_data, threshold=th)
        p3, r3, _ = evaluate_prediction(heatmap_data, predictions_hd, threshold=th)

        pr_llm.append(p1)
        rc_llm.append(r1)
        pr_yo.append(p2)
        rc_yo.append(r2)
        pr_hd.append(p3)
        rc_hd.append(r3)

    plt.figure(figsize=(8, 6))
    plt.plot(rc_llm, pr_llm, marker='o', label='LLM only', color='blue')
    plt.plot(rc_yo, pr_yo, marker='o', label='EchoFusion', color='red')
    plt.plot(rc_hd, pr_hd, marker='o', label='Video & Audio feature only', color='green')

    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision–Recall Curve (Threshold sweep)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# 실행 예시
if __name__ == "__main__":
    heatmap_path = "heatmap_dataset.jsonl"
    summarized_path = "summarized_results.jsonl"   # LLM Only
    predictions_path = "predictions.jsonl"          # Yo Pipeline
    hd_path = "predictions_hd.jsonl"                 # HD Pipeline

    plot_precision_recall_curves(heatmap_path, summarized_path, predictions_path, hd_path)
