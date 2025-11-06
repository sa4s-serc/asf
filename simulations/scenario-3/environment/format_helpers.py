"""Helper functions to format dict results as readable strings."""

from typing import Dict, Any, List
import json


def format_dict_as_text(data: Dict[str, Any], title: str = None) -> str:
    """Format a dictionary as readable text."""
    lines = []

    if title:
        lines.append(title)
        lines.append("")

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    lines.append(f"  {sub_key}:")
                    for k, v in sub_value.items():
                        lines.append(f"    {k}: {v}")
                else:
                    lines.append(f"  {sub_key}: {sub_value}")
        elif isinstance(value, list):
            lines.append(f"{key}: {len(value)} items")
            for item in value[:5]:  # Show first 5 items
                if isinstance(item, dict):
                    lines.append(f"  - {json.dumps(item, indent=4)}")
                else:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")

    return "\n".join(lines)
