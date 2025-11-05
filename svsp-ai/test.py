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

def calc_overlap(a, b):
    """두 구간 (start, end)의 겹치는 길이 계산"""
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))

def f1_highlight_score(heatmap_path, result_path, threshold=0.5):
    heatmap_data = {item['id']: item['h'] for item in load_jsonl(heatmap_path)}
    result_data = {item['id']: item['result']['timestamps'] for item in load_jsonl(result_path)}

    metrics = {}

    for vid, pred_intervals in result_data.items():
        if vid not in heatmap_data:
            continue

        gt_intervals = convert_heatmap_to_intervals(heatmap_data[vid], threshold)

        # 전체 길이 (모든 heatmap t 값의 범위로 계산)
        t_values = [p['t'] for p in heatmap_data[vid]]
        total_time = max(t_values) - min(t_values)

        # 각 비디오별 시간 기반 TP, FP, FN 계산
        tp, fp, fn = 0, 0, 0

        # 1초 단위로 샘플링 (정밀도 조절 가능)
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

    # 전체 평균
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
    results_path = "summarized_results.jsonl"
    metrics, avg = f1_highlight_score(heatmap_path, results_path, threshold=0.5)
    print("\n각 비디오별 F1 점수:")
    for vid, m in metrics.items():
        print(f"{vid}: F1={m['f1']:.4f}, Precision={m['precision']:.4f}, Recall={m['recall']:.4f}")