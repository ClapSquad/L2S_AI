"""
ASS Subtitle Generator for Karaoke-Style Subtitles

This module creates beautiful, animated subtitles that:
1. Display words centered on screen
2. Highlight the current word being spoken (like karaoke)
3. Support multiple visual styles
4. Are fully customizable
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ============================================================================
# STYLE DEFINITIONS
# ============================================================================

class SubtitleStyleType(Enum):
    """
    Available subtitle styles matching frontend options.
    
    These correspond to the SubtitleStyleSelector component options.
    """
    SIMPLE1 = "simple1"    # White text + black outline
    SIMPLE2 = "simple2"    # Black text + white background
    SIMPLE3 = "simple3"    # White text + black background
    CASUAL = "casual"      # Stylized with shadow (Korean/casual feel)
    DYNAMIC = "dynamic"    # Word-by-word karaoke highlighting


@dataclass
class SubtitleStyleConfig:
    """
    Configuration for a single subtitle style.
    
    ASS uses a specific format for colors: &HAABBGGRR
    - AA = Alpha (transparency): 00 = opaque, FF = transparent
    - BB = Blue component
    - GG = Green component  
    - RR = Red component
    
    Notice it's BGR, not RGB! So yellow (#FFFF00) becomes &H00FFFF&
    """
    # Font settings
    font_name: str = "Arial"
    font_size: int = 48
    bold: bool = True
    
    # Colors (ASS format: &HAABBGGRR&)
    primary_color: str = "&H00FFFFFF&"      # Main text color (white)
    secondary_color: str = "&H00FFFFFF&"    # For karaoke fill (white)
    outline_color: str = "&H00000000&"      # Outline color (black)
    back_color: str = "&H80000000&"         # Background/shadow color (semi-transparent black)
    
    # Highlight color for karaoke (active word)
    highlight_color: str = "&H0000FFFF&"    # Yellow in ASS BGR format
    
    # Outline and shadow
    outline_width: float = 3.0
    shadow_depth: float = 2.0
    
    # Positioning (ASS alignment: 1-9 like numpad, 2 = bottom center, 5 = middle center)
    alignment: int = 2  # Bottom center
    margin_vertical: int = 50  # Distance from bottom
    
    # Border style: 1 = outline + shadow, 3 = opaque box
    border_style: int = 1


# Pre-defined style configurations
STYLE_CONFIGS: Dict[SubtitleStyleType, SubtitleStyleConfig] = {
    SubtitleStyleType.SIMPLE1: SubtitleStyleConfig(
        font_name="Arial",
        font_size=52,
        bold=True,
        primary_color="&H00FFFFFF&",        # White
        outline_color="&H00000000&",        # Black outline
        highlight_color="&H0000FFFF&",      # Yellow highlight
        outline_width=4.0,
        shadow_depth=0.0,
        border_style=1,
        alignment=2,
        margin_vertical=60
    ),
    
    SubtitleStyleType.SIMPLE2: SubtitleStyleConfig(
        font_name="Arial",
        font_size=48,
        bold=True,
        primary_color="&H00000000&",        # Black text
        back_color="&H80FFFFFF&",           # Semi-transparent white background
        highlight_color="&H00FF8000&",      # Orange highlight
        outline_width=0.0,
        shadow_depth=0.0,
        border_style=3,                      # Opaque box background
        alignment=2,
        margin_vertical=60
    ),
    
    SubtitleStyleType.SIMPLE3: SubtitleStyleConfig(
        font_name="Arial",
        font_size=48,
        bold=True,
        primary_color="&H00FFFFFF&",        # White text
        back_color="&H80000000&",           # Semi-transparent black background
        highlight_color="&H0000FF00&",      # Green highlight
        outline_width=0.0,
        shadow_depth=0.0,
        border_style=3,                      # Opaque box background
        alignment=2,
        margin_vertical=60
    ),
    
    SubtitleStyleType.CASUAL: SubtitleStyleConfig(
        font_name="Jua",                     # Korean-friendly font
        font_size=54,
        bold=True,
        primary_color="&H00FFFFFF&",        # White
        outline_color="&H00000000&",        # Black outline
        highlight_color="&H0000FFFF&",      # Yellow highlight
        outline_width=4.0,
        shadow_depth=3.0,
        border_style=1,
        alignment=2,
        margin_vertical=60
    ),
    
    SubtitleStyleType.DYNAMIC: SubtitleStyleConfig(
        font_name="Impact",                  # Bold, impactful font
        font_size=56,
        bold=True,
        primary_color="&H00FFFFFF&",        # White
        outline_color="&H00000000&",        # Black outline
        highlight_color="&H0014FF39&",      # Neon green (#39FF14 in BGR)
        outline_width=4.0,
        shadow_depth=2.0,
        border_style=1,
        alignment=5,                         # Middle center for dynamic
        margin_vertical=0
    ),
}


# ============================================================================
# ASS FILE GENERATOR
# ============================================================================

@dataclass
class WordTiming:
    """Simple structure for word timing information"""
    word: str
    start: float
    end: float


def seconds_to_ass_time(seconds: float) -> str:
    """
    Convert seconds to ASS timestamp format.
    
    ASS uses: H:MM:SS.cc (centiseconds, not milliseconds!)
    
    Example: 65.123 seconds -> "0:01:05.12"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def generate_ass_header(
    style_type: SubtitleStyleType = SubtitleStyleType.DYNAMIC,
    video_width: int = 1080,
    video_height: int = 1920,
    custom_config: Optional[SubtitleStyleConfig] = None
) -> str:
    """
    Generate the header section of an ASS file.
    
    The header contains:
    - Script info (title, resolution, etc.)
    - Style definitions (fonts, colors, positioning)
    
    Think of this like the <head> section of an HTML file - it sets up
    all the styling before the actual content.
    """
    config = custom_config or STYLE_CONFIGS.get(style_type, STYLE_CONFIGS[SubtitleStyleType.DYNAMIC])
    
    header = f"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.font_name},{config.font_size},{config.primary_color},{config.secondary_color},{config.outline_color},{config.back_color},{1 if config.bold else 0},0,0,0,100,100,0,0,{config.border_style},{config.outline_width},{config.shadow_depth},{config.alignment},10,10,{config.margin_vertical},1
Style: Highlight,{config.font_name},{int(config.font_size * 1.15)},{config.highlight_color},{config.highlight_color},{config.outline_color},{config.back_color},{1 if config.bold else 0},0,0,0,100,100,0,0,{config.border_style},{config.outline_width + 1},{config.shadow_depth},{config.alignment},10,10,{config.margin_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


def generate_karaoke_line(
    words: List[WordTiming],
    style_type: SubtitleStyleType = SubtitleStyleType.DYNAMIC,
    words_per_line: int = 4
) -> List[str]:
    """
    Generate ASS dialogue lines for karaoke-style highlighting.
    
    This creates subtitle events where:
    1. All words in a group are shown
    2. The currently spoken word is highlighted
    3. Words animate smoothly from white to highlighted color
    
    How it works:
    For a sentence like "Hello beautiful world today", we might show:
    - Line 1 (0.0s - 2.0s): "Hello beautiful" with each word highlighted when spoken
    - Line 2 (2.0s - 4.0s): "world today" with each word highlighted when spoken
    
    The {\k} tags in ASS control the karaoke timing (in centiseconds).
    """
    if not words:
        return []
    
    config = STYLE_CONFIGS.get(style_type, STYLE_CONFIGS[SubtitleStyleType.DYNAMIC])
    events = []
    
    # Group words into lines
    word_groups = []
    for i in range(0, len(words), words_per_line):
        group = words[i:i + words_per_line]
        if group:
            word_groups.append(group)
    
    for group in word_groups:
        if not group:
            continue
            
        group_start = group[0].start
        group_end = group[-1].end
        
        # Method 1: Individual events for each word (more control)
        # This shows the entire line but changes which word is highlighted
        
        for word_idx, current_word in enumerate(group):
            # Build the text with the current word highlighted
            text_parts = []
            
            for idx, w in enumerate(group):
                if idx == word_idx:
                    # This word is currently being spoken - use highlight style
                    # {\rHighlight} switches to Highlight style
                    # {\r} at the end resets to Default style
                    text_parts.append(f"{{\\rHighlight}}{w.word.upper()}{{\\r}}")
                else:
                    # Other words use default style
                    text_parts.append(w.word.upper())
            
            full_text = " ".join(text_parts)
            
            event = f"Dialogue: 0,{seconds_to_ass_time(current_word.start)},{seconds_to_ass_time(current_word.end)},Default,,0,0,0,,{full_text}"
            events.append(event)
    
    return events


def generate_simple_karaoke_line(
    words: List[WordTiming],
    style_type: SubtitleStyleType = SubtitleStyleType.DYNAMIC,
    words_per_line: int = 5,
    max_line_duration: float = 3.0
) -> List[str]:
    """
    Alternative karaoke generation using ASS {\kf} tags.
    
    This is a simpler approach that uses ASS's built-in karaoke feature.
    The {\kf} tag creates a smooth "fill" effect from left to right.
    
    {\kf100} means "take 100 centiseconds (1 second) to fill this text"
    
    This creates effects like:
    "HELLO" fills with yellow from H→E→L→L→O over 0.5 seconds
    """
    if not words:
        return []
    
    events = []
    config = STYLE_CONFIGS.get(style_type, STYLE_CONFIGS[SubtitleStyleType.DYNAMIC])
    
    # Group words into display lines
    current_group = []
    group_start = None
    
    for word in words:
        if not current_group:
            group_start = word.start
            current_group.append(word)
        elif (len(current_group) >= words_per_line or 
              word.end - group_start > max_line_duration):
            # Finish current group and start new one
            events.extend(_create_kf_event(current_group, group_start, config))
            current_group = [word]
            group_start = word.start
        else:
            current_group.append(word)
    
    # Don't forget the last group
    if current_group:
        events.extend(_create_kf_event(current_group, group_start, config))
    
    return events


def _create_kf_event(
    words: List[WordTiming],
    group_start: float,
    config: SubtitleStyleConfig
) -> List[str]:
    """Helper to create karaoke-fill events for a word group"""
    if not words:
        return []
    
    # Build text with {\kf} timing tags
    text_parts = []
    for word in words:
        # Duration in centiseconds
        duration_cs = int((word.end - word.start) * 100)
        # {\kf} = karaoke fill effect
        text_parts.append(f"{{\\kf{duration_cs}}}{word.word.upper()}")
    
    full_text = " ".join(text_parts)
    group_end = words[-1].end
    
    # Add slight padding to avoid gaps
    event = f"Dialogue: 0,{seconds_to_ass_time(group_start)},{seconds_to_ass_time(group_end + 0.1)},Default,,0,0,0,,{full_text}"
    
    return [event]


def generate_word_by_word_events(
    words: List[WordTiming],
    style_type: SubtitleStyleType = SubtitleStyleType.DYNAMIC,
    words_per_line: int = 3,
    min_display_duration: float = 0.3
) -> List[str]:
    """
    Generate events showing one word at a time, enlarged and centered.
    
    This is the most impactful style for short-form content:
    - Only shows 1-3 words at a time
    - Large, bold text
    - Current word is highlighted/enlarged
    
    Perfect for TikTok/Reels style captions!
    """
    if not words:
        return []
    
    events = []
    config = STYLE_CONFIGS.get(style_type, STYLE_CONFIGS[SubtitleStyleType.DYNAMIC])
    
    i = 0
    while i < len(words):
        # Get current group of words
        group = words[i:i + words_per_line]
        
        if not group:
            break
        
        group_start = group[0].start
        group_end = group[-1].end
        
        # Ensure minimum display duration
        if group_end - group_start < min_display_duration:
            group_end = group_start + min_display_duration
        
        # For each word in the group, create an event where that word is highlighted
        for word_idx, current_word in enumerate(group):
            text_parts = []
            
            for idx, w in enumerate(group):
                if idx == word_idx:
                    # Highlighted word: larger size using {\fs} tag
                    # {\c&H..&} changes primary color
                    highlight_text = f"{{\\c{config.highlight_color}\\fs{int(config.font_size * 1.2)}}}{w.word.upper()}{{\\r}}"
                    text_parts.append(highlight_text)
                else:
                    text_parts.append(w.word.upper())
            
            full_text = " ".join(text_parts)
            
            # Calculate timing
            word_start = current_word.start
            word_end = current_word.end
            
            # Ensure minimum duration
            if word_end - word_start < min_display_duration:
                word_end = word_start + min_display_duration
            
            event = f"Dialogue: 0,{seconds_to_ass_time(word_start)},{seconds_to_ass_time(word_end)},Default,,0,0,0,,{full_text}"
            events.append(event)
        
        i += words_per_line
    
    return events


# ============================================================================
# MAIN GENERATION FUNCTION
# ============================================================================

def generate_karaoke_ass(
    words: List[Dict],  # List of {"word": str, "start": float, "end": float}
    output_path: str,
    style_type: str = "dynamic",
    video_width: int = 1080,
    video_height: int = 1920,
    words_per_line: int = 3,
    karaoke_mode: str = "highlight"  # "highlight", "fill", or "word_by_word"
) -> str:
    """
    Main function to generate a karaoke-style ASS subtitle file.
    
    Args:
        words: List of word dictionaries with timing info
               [{"word": "Hello", "start": 0.0, "end": 0.4}, ...]
        output_path: Where to save the .ass file
        style_type: One of "simple1", "simple2", "simple3", "casual", "dynamic"
        video_width: Video width in pixels (for positioning)
        video_height: Video height in pixels
        words_per_line: How many words to show at once
        karaoke_mode: 
            - "highlight": Each word changes style when spoken
            - "fill": Words fill with color using {\kf} animation
            - "word_by_word": Show only current word group, highlight active word
    
    Returns:
        Path to the generated ASS file
    
    Example:
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.4},
            {"word": "world", "start": 0.5, "end": 0.9}
        ]
        generate_karaoke_ass(words, "output.ass", style_type="dynamic")
    """
    # Convert style string to enum
    try:
        style_enum = SubtitleStyleType(style_type.lower())
    except ValueError:
        logging.warning(f"Unknown style '{style_type}', using 'dynamic'")
        style_enum = SubtitleStyleType.DYNAMIC
    
    # Convert dictionaries to WordTiming objects
    word_timings = [
        WordTiming(
            word=w.get("word", ""),
            start=w.get("start", 0.0),
            end=w.get("end", 0.0)
        )
        for w in words
        if w.get("word", "").strip()  # Skip empty words
    ]
    
    if not word_timings:
        raise ValueError("No valid words provided for subtitle generation")
    
    # Generate ASS content
    header = generate_ass_header(style_enum, video_width, video_height)
    
    # Choose karaoke generation method
    if karaoke_mode == "fill":
        events = generate_simple_karaoke_line(word_timings, style_enum, words_per_line)
    elif karaoke_mode == "word_by_word":
        events = generate_word_by_word_events(word_timings, style_enum, words_per_line)
    else:  # "highlight" is default
        events = generate_karaoke_line(word_timings, style_enum, words_per_line)
    
    # Combine header and events
    ass_content = header + "\n".join(events)
    
    # Write to file
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    
    logging.info(f"Generated karaoke ASS file: {output_path}")
    logging.info(f"  - Style: {style_type}")
    logging.info(f"  - Words: {len(word_timings)}")
    logging.info(f"  - Events: {len(events)}")
    
    return output_path


# ============================================================================
# INTEGRATION HELPER
# ============================================================================

def transcribe_and_generate_karaoke(
    audio_path: str,
    output_ass_path: str,
    whisper_model: str = "base",
    style_type: str = "dynamic",
    video_width: int = 1080,
    video_height: int = 1920,
    words_per_line: int = 3,
    karaoke_mode: str = "word_by_word"
) -> str:
    """
    One-stop function: transcribe audio and generate karaoke subtitles.
    
    This combines transcription and ASS generation into a single call,
    making it easy to integrate into your pipeline.
    
    Example:
        ass_file = transcribe_and_generate_karaoke(
            "video_audio.mp3",
            "output/subtitles.ass",
            style_type="dynamic"
        )
    """
    # Import here to avoid circular dependency if these modules call each other.
    from src.core.audio_processing.audio_to_text_enhanced import transcribe_for_karaoke
    
    # Step 1: Transcribe with word timestamps
    logging.info(f"Transcribing audio: {audio_path}")
    words = transcribe_for_karaoke(audio_path, whisper_model)
    
    if isinstance(words, str):  # Error occurred
        raise RuntimeError(f"Transcription failed: {words}")
    
    # Step 2: Generate ASS file
    logging.info(f"Generating karaoke subtitles...")
    return generate_karaoke_ass(
        words=words,
        output_path=output_ass_path,
        style_type=style_type,
        video_width=video_width,
        video_height=video_height,
        words_per_line=words_per_line,
        karaoke_mode=karaoke_mode
    )


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Generate karaoke-style ASS subtitles from word timing data"
    )
    parser.add_argument(
        "input_json",
        type=str,
        help="JSON file with word timing data"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output.ass",
        help="Output ASS file path"
    )
    parser.add_argument(
        "--style",
        type=str,
        default="dynamic",
        choices=["simple1", "simple2", "simple3", "casual", "dynamic"],
        help="Subtitle style"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1080,
        help="Video width"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1920,
        help="Video height"
    )
    parser.add_argument(
        "--words-per-line",
        type=int,
        default=3,
        help="Maximum words to show at once"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="word_by_word",
        choices=["highlight", "fill", "word_by_word"],
        help="Karaoke animation mode"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Load word timing data
    with open(args.input_json, 'r', encoding='utf-8') as f:
        words = json.load(f)
    
    # Generate ASS file
    output_path = generate_karaoke_ass(
        words=words,
        output_path=args.output,
        style_type=args.style,
        video_width=args.width,
        video_height=args.height,
        words_per_line=args.words_per_line,
        karaoke_mode=args.mode
    )
    
    print(f"\n✅ Generated: {output_path}")