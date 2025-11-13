import argparse
import json
import os
import pathlib
from typing import List, Dict, Any
import numpy as np

# --- Path setup for utils import ---
import sys
# Add the project root to the Python path to allow importing from 'utils'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End Path setup ---

from utils.highlight_detection.highlight_pipeline import run_echofusion
from utils.logging_initialization import initialize_logging

# Usage
# python evaluation/eval.py --ground_truth <ground_truth_jsonl> -- predictions <predictions_jsonl>

def calculate_tiou(pred_segment: List[float], gt_segment: List[float]) -> float:
    """Calculates temporal Intersection over Union."""
    pred_start, pred_end = pred_segment
    gt_start, gt_end = gt_segment

    intersection_start = max(pred_start, gt_start)
    intersection_end = min(pred_end, gt_end)
    intersection = max(0, intersection_end - intersection_start)

    union = (pred_end - pred_start) + (gt_end - gt_start) - intersection
    return intersection / union if union > 0 else 0.0

def compute_hit_at_delta(pred_starts, gt_timestamps, delta=2.0):
    hits = sum(any(abs(p - g) <= delta for g in gt_timestamps)
               for p in pred_starts)
    precision = hits / len(pred_starts)
    recall = hits / len(gt_timestamps)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def iou_at_topk_percent(pred_segments, gt_times, duration, k_percent=10):
    step = 1.0  # seconds per sample
    t = np.arange(0, duration, step)
    pred_score = np.zeros_like(t)
    gt_score = np.zeros_like(t)
    # assign scores
    for s, e, sc in [(p["start"], p["end"], p["score"]) for p in pred_segments]:
        pred_score[(t >= s) & (t <= e)] = np.maximum(pred_score[(t >= s) & (t <= e)], sc)
    for g in gt_times:
        gt_score[(t >= g-1) & (t <= g+1)] = 1.0  # windowed GT
    # top-K%
    k = int(len(t) * k_percent/100)
    pred_mask = np.zeros_like(t, bool)
    gt_mask = np.zeros_like(t, bool)
    pred_mask[np.argsort(pred_score)[-k:]] = True
    gt_mask[np.argsort(gt_score)[-k:]] = True
    return np.sum(pred_mask & gt_mask) / np.sum(pred_mask | gt_mask)


def evaluate(predictions_path: str, ground_truth_path: str, tiou_threshold: float = 0.5, gt_window_seconds: float = 2.0):
    """
    Run evaluation against ground truth.
    Calculates TP/FP/FN, Precision, Recall, F1, and mAP.

    Args:
        predictions_path (str): Path to the prediction JSONL file.
        ground_truth_path (str): Path to the ground truth JSONL file.
        tiou_threshold (float): Threshold for a prediction to be a True Positive.
        gt_window_seconds (float): Creates a GT segment of [t-w, t+w] around a GT timestamp `t`.
    """
    print(f"\n--- Starting Evaluation ---")
    print(f"Predictions: {predictions_path}")
    print(f"Ground Truth: {ground_truth_path}")
    print(f"tIoU Threshold: {tiou_threshold}")
    print(f"GT Window: ±{gt_window_seconds}s")

    # Load predictions
    preds: Dict[str, Dict[str, Any]] = {}

    with open(predictions_path, "r") as f:
        first_line = True
        for line in f:
            data = json.loads(line)
            # Sort by score descending for mAP calculation
            sorted_highlights = sorted(data["highlights"], key=lambda x: x["score"], reverse=True)
            # Get video duration from the last highlight's end time if available
            duration = max(h['end'] for h in sorted_highlights) if sorted_highlights else 0
            preds[data["video_name"]] = {"highlights": sorted_highlights, "duration": duration}
            if first_line:
                print("--- Content of 'preds' dictionary ---")
                print(json.dumps(preds[data["video_name"]], indent=2))
                first_line = False

    # Load ground truth and convert timestamps to segments
    gts: Dict[str, Dict[str, Any]] = {}
    with open(ground_truth_path, "r") as f:
        first_line = True
        for line in f:
            data = json.loads(line)
            # Assuming format is {"id": "...", "h": [{"t": ...}]}
            video_id = data["id"]
            if not any(str(video_id + ext) in preds for ext in ["", ".mp4", ".mkv", ".avi", ".mov", ".flv"]):
                 # the id in predictions might include file extension
                 # this is too bothersome so we should normalize the video_id for the predictions keys (check run.py)
                continue  # Skip GTs without predictions
            gt_timestamps = [item["t"] for item in data["h"]]
            gt_segments = [[t - gt_window_seconds, t + gt_window_seconds] for t in gt_timestamps]
            gts[video_id] = {"segments": gt_segments, "timestamps": gt_timestamps}
            if first_line:
                print("--- Content of 'gts' dictionary ---")
                print(json.dumps(gts[video_id], indent=2))
                first_line = False

    total_tp, total_fp, total_fn = 0, 0, 0
    average_precisions = []
    tp_tiou_scores = []
    top_k_values = [5, 10] # Fixed K values for Top-K analysis
    top_k_tiou_scores = {k: [] for k in top_k_values}

    all_hit_at_delta_precisions, all_hit_at_delta_recalls = [], []
    all_iou_at_topk = []

    video_names = sorted(list(gts.keys()))

    for video_name in video_names:
        # Match GT `video_name` (which might be an ID) with prediction `video_name` (which is a filename)
        # This handles cases where GT has "aOwmt39L2IQ" and predictions have "aOwmt39L2IQ.mp4"
        pred_key = None
        match_found = 0
        for p_key in preds.keys():
            if p_key.startswith(video_name):
                print("✅ Match found.")
                match_found += 1
                pred_key = p_key
                break

        # if not pred_key:
        #     print(f"⚠️ No predictions found for video: {video_name}")
        #     continue

        pred_segments = preds[pred_key]["highlights"]
        gt_segments = gts[video_name]["segments"]
        gt_timestamps = gts[video_name]["timestamps"]
        num_preds = len(pred_segments)
        # num_gt = len(gt_segments)
        num_gt = len(gt_timestamps)

        if not pred_segments:
            print(f"⚠️ No predictions for video: {video_name}. Counting all GT as FN.")
            total_fn += num_gt
            continue

        # --- TP/FP/FN Calculation ---
        gt_matched = [False] * num_gt
        tp, fp = 0, 0

        for pred in pred_segments:
            best_tiou = 0
            best_gt_idx = -1
            for i, gt in enumerate(gt_segments):
                tiou = calculate_tiou([pred["start"], pred["end"]], gt)
                if tiou > best_tiou:
                    best_tiou = tiou
                    best_gt_idx = i

            if best_tiou >= tiou_threshold and not gt_matched[best_gt_idx]:
                tp += 1
                gt_matched[best_gt_idx] = True
                tp_tiou_scores.append(best_tiou)
                print(f"  [TP] Match in '{pred_key}': pred [{pred['start']:.2f}-{pred['end']:.2f}] | gt [{gt_segments[best_gt_idx][0]:.2f}-{gt_segments[best_gt_idx][1]:.2f}] | tIoU: {best_tiou:.4f}")
            else:
                fp += 1

        fn = num_gt - sum(gt_matched)
        total_tp += tp
        total_fp += fp
        total_fn += fn

        # --- Top-K tIoU Calculation (based on rank) ---
        if num_preds > 0 and num_gt > 0:
            for pred in pred_segments:
                # Check if the prediction's rank falls into one of our K buckets
                for k in top_k_values:
                    if pred['rank'] <= k:
                        best_tiou = 0
                        for gt in gt_segments:
                            tiou = calculate_tiou([pred["start"], pred["end"]], gt)
                            best_tiou = max(best_tiou, tiou)
                        top_k_tiou_scores[k].append(best_tiou)
        
        # --- Hit@Delta Calculation ---
        if num_preds > 0 and num_gt > 0:
            pred_starts = [p["start"] for p in pred_segments]
            precision, recall, _ = compute_hit_at_delta(pred_starts, gt_timestamps)
            all_hit_at_delta_precisions.append(precision)
            all_hit_at_delta_recalls.append(recall)

        # --- IoU@TopK% Calculation ---
        if num_preds > 0 and num_gt > 0:
            video_duration = preds[pred_key]["duration"]
            if video_duration > 0:
                iou_top10 = iou_at_topk_percent(pred_segments, gt_timestamps, video_duration, k_percent=10)
                all_iou_at_topk.append(iou_top10)

        # --- mAP Calculation ---
        if num_gt > 0:
            hits = np.zeros(len(pred_segments))
            gt_matched_map = [False] * num_gt
            for i, pred in enumerate(pred_segments):
                # Find best matching GT segment for this prediction
                best_tiou, best_gt_idx = -1, -1
                for j, gt in enumerate(gt_segments):
                    tiou = calculate_tiou([pred["start"], pred["end"]], gt)
                    if tiou > best_tiou:
                        best_tiou, best_gt_idx = tiou, j
                
                if best_tiou >= tiou_threshold and not gt_matched_map[best_gt_idx]:
                    hits[i] = 1
                    gt_matched_map[best_gt_idx] = True

            if np.sum(hits) > 0:
                precision_at_k = np.cumsum(hits) / (np.arange(len(pred_segments)) + 1)
                average_precision = np.sum(precision_at_k * hits) / num_gt
                average_precisions.append(average_precision)

    # --- Aggregate Metrics ---
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    mean_ap = np.mean(average_precisions) if average_precisions else 0.0
    avg_tp_tiou = np.mean(tp_tiou_scores) if tp_tiou_scores else 0.0
    
    avg_hit_precision = np.mean(all_hit_at_delta_precisions) if all_hit_at_delta_precisions else 0.0
    avg_hit_recall = np.mean(all_hit_at_delta_recalls) if all_hit_at_delta_recalls else 0.0
    avg_iou_topk = np.mean(all_iou_at_topk) if all_iou_at_topk else 0.0

    print("\n--- Evaluation Results ---")
    print(f"Total True Positives (TP):  {total_tp}")
    print(f"Total False Positives (FP): {total_fp}")
    print(f"Total False Negatives (FN): {total_fn}")
    print("--------------------------")
    print(f"Avg. tIoU of TPs (tIoU > {tiou_threshold}):      {avg_tp_tiou:.4f}")
    for k, scores in top_k_tiou_scores.items():
        avg_top_k_tiou = np.mean(scores) if scores else 0.0
        print(f"Avg. tIoU @ Top-{k} Predictions:        {avg_top_k_tiou:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"mAP:       {mean_ap:.4f}")
    print(f"Avg. Hit Precision (delta=2s):   {avg_hit_precision:.4f}")
    print(f"Avg. Hit Recall (delta=2s):      {avg_hit_recall:.4f}")
    print(f"Avg. IoU @ Top-10%:              {avg_iou_topk:.4f}")
    print("--------------------------\n")

def main():

    initialize_logging()

    parser = argparse.ArgumentParser(description="Evaluation script for video summarization.")
    parser.add_argument(
        "-g", "--ground_truth",
        type=str,
        required=True,
        help="Path to the ground truth JSONL file."
    )
    parser.add_argument("-p", "--predictions", type=str, required=True, help="Path to the predictions JSONL file.")
    parser.add_argument("--tiou_threshold", type=float, default=0.5, help="tIoU threshold for TP/FP classification.")
    parser.add_argument("--gt_window", type=float, default=2.0, help="Window size (+/- seconds) around a GT timestamp.")

    args = parser.parse_args()

    evaluate(
        predictions_path=args.predictions,
        ground_truth_path=args.ground_truth,
        tiou_threshold=args.tiou_threshold,
        gt_window_seconds=args.gt_window
    )

if __name__ == "__main__":
    main()