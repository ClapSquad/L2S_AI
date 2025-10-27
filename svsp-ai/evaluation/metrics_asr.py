from jiwer import wer
from typing import List, Union

import jiwer

# WER
# Language Detection Accuracy

def calculate_wer(ground_truth: Union[str, List[str]], hypothesis: Union[str, List[str]]) -> float:
    """
    Calculates the Word Error Rate (WER) between ground truth and hypothesis texts
    using the jiwer library.

    Args:
        ground_truth: The reference sentence(s). Can be a single string or a list of strings.
        hypothesis: The transcribed sentence(s). Can be a single string or a list of strings.

    Returns:
        The Word Error Rate as a float (0.0 to 1.0+).
    """
    # A standard transformation for ASR evaluation.
    # This ensures that differences in capitalization, punctuation, and spacing
    # do not unfairly penalize the ASR model.
    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemovePunctuation(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
    ])

    # Calculate WER
    wer_score = jiwer.wer(ground_truth, hypothesis, truth_transform=transformation, hypothesis_transform=transformation)
    return wer_score
