import json
import numpy as np

def load_jsonl(path):
    """jsonl 파일을 한 줄씩 읽어 리스트로 반환"""
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def convert_heatmap_to_intervals(heatmap, threshold=0.5):
    """
    heatmap 데이터를 threshold 기준으로 하이라이트 구간으로 변환
    """
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

def f1_highlight_score_for_prediction2(heatmap_path, pred_path, threshold=0.5):
    """
    prediction2 (predictions.jsonl) 파일을 heatmap 라벨과 비교하여 F1, Precision, Recall 계산
    """
    # load label
    heatmap_data = {item['id']: item['h'] for item in load_jsonl(heatmap_path)}

    # load prediction2
    pred_data_raw = load_jsonl(pred_path)
    pred_data = {}
    for item in pred_data_raw:
        vid = item['video_name'].replace('.mp4', '')
        pred_data[vid] = [(h['start'], h['end']) for h in item['highlights']]

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

        metrics[vid] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn
        }

    mean_f1 = np.mean([m["f1"] for m in metrics.values()]) if metrics else 0
    mean_precision = np.mean([m["precision"] for m in metrics.values()]) if metrics else 0
    mean_recall = np.mean([m["recall"] for m in metrics.values()]) if metrics else 0

    print(f"전체 평균 Precision: {mean_precision:.4f}")
    print(f"전체 평균 Recall: {mean_recall:.4f}")
    print(f"전체 평균 F1-score: {mean_f1:.4f}")

    return metrics, {"precision": mean_precision, "recall": mean_recall, "f1": mean_f1}


# 실행 예시
if __name__ == "__main__":
    heatmap_path = "heatmap_dataset.jsonl"
    pred2_path = "predictions.jsonl"
    metrics, avg = f1_highlight_score_for_prediction2(heatmap_path, pred2_path, threshold=0.5)

    print("\n각 비디오별 F1 점수:")
    for vid, m in metrics.items():
        print(f"{vid}: F1={m['f1']:.4f}, Precision={m['precision']:.4f}, Recall={m['recall']:.4f}")
