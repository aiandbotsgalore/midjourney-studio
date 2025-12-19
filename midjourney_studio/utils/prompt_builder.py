"""
Prompt construction utilities for Midjourney parameters.
"""

import re
from typing import Dict, Any, List


def build_prompt(base_prompt: str, params: Dict[str, Any]) -> str:
    """
    Construct full MJ prompt with parameters.
    Ref: post-midjourney-jobs-imagine.md - prompt construction

    Args:
        base_prompt: Base text prompt
        params: Dictionary of MJ parameters (ar, version, stylize, etc.)

    Returns:
        Complete prompt string with all parameters
    """
    parts = [base_prompt.strip()]

    # Aspect ratio
    if params.get("ar") and params["ar"] != "1:1":
        parts.append(f"--ar {params['ar']}")

    # Model version
    if params.get("version") and params["version"] != "default":
        if "niji" in params["version"]:
            parts.append(f"--{params['version']}")
        else:
            parts.append(f"--v {params['version']}")

    # Stylize
    if params.get("stylize"):
        parts.append(f"--s {params['stylize']}")

    # Chaos
    if params.get("chaos") and params["chaos"] > 0:
        parts.append(f"--c {params['chaos']}")

    # Quality
    if params.get("quality") and params["quality"] != "1":
        parts.append(f"--q {params['quality']}")

    # Weird
    if params.get("weird") and params["weird"] > 0:
        parts.append(f"--weird {params['weird']}")

    # Seed
    if params.get("seed"):
        parts.append(f"--seed {params['seed']}")

    # Tile
    if params.get("tile"):
        parts.append("--tile")

    # Raw mode
    if params.get("raw"):
        parts.append("--raw")

    # Video generation
    if params.get("video"):
        parts.append("--video")
        # Note: --motion and --loop are not standard Midjourney parameters 
        # as of V6. They are often used in other models like Luma/Runway.
        # Removing them here ensures the Midjourney API doesn't reject the prompt.

    # No parameters (negative prompts)
    if params.get("no"):
        parts.append(f"--no {params['no']}")

    # Style reference with weight
    if params.get("sref"):
        parts.append(f"--sref {params['sref']}")
        if params.get("sw") and params["sw"] != 100:
            parts.append(f"--sw {params['sw']}")

    # Character reference with weight
    if params.get("cref"):
        parts.append(f"--cref {params['cref']}")
        if params.get("cw") and params["cw"] != 100:
            parts.append(f"--cw {params['cw']}")

    # Image weight (for image prompts)
    if params.get("iw") and params["iw"] != 1.0:
        parts.append(f"--iw {params['iw']}")

    # Turbo mode
    if params.get("turbo"):
        parts.append("--turbo")

    return " ".join(parts)


def parse_describe_prompts(embed_description: str) -> List[str]:
    """
    Parse the 4 prompt suggestions from /describe response.
    Ref: post-midjourney-jobs-describe.md - response.embeds[0].description

    Args:
        embed_description: The embeds[0].description field from describe response

    Returns:
        List of 4 prompt suggestions
    """
    prompts = []
    # Pattern: 1️⃣ prompt text --ar X:Y\n\n2️⃣ ...
    pattern = r'[1-4]️⃣\s*(.+?)(?=\n\n[1-4]️⃣|\Z)'
    matches = re.findall(pattern, embed_description, re.DOTALL)

    for match in matches:
        prompt = match.strip()
        prompts.append(prompt)

    return prompts if prompts else [embed_description]


def sanitize_prompt(prompt: str) -> str:
    """
    Sanitize user input prompt to prevent issues.

    Args:
        prompt: User input prompt

    Returns:
        Sanitized prompt
    """
    # Remove excessive whitespace
    prompt = " ".join(prompt.split())

    # Trim to reasonable length (Midjourney has ~4000 char limit)
    if len(prompt) > 4000:
        prompt = prompt[:4000]

    return prompt.strip()
