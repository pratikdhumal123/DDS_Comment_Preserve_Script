from typing import List


def paragraph_style(kind: str) -> str:
    if kind == "deleted":
        return "background-color:#ffebee;color:#b71c1c;border-left:3px solid #e53935;padding-left:6px;text-decoration:line-through;text-decoration-thickness:2px;"
    if kind == "replaced":
        return "background-color:#e3f2fd;color:#0d47a1;border-left:3px solid #1e88e5;padding-left:6px;"
    return "background-color:#e8f5e9;color:#1b5e20;border-left:3px solid #2e7d32;padding-left:6px;"


def inline_span_style(kind: str) -> str:
    if kind == "deleted":
        return (
            "background-color:#ffebee;color:#b71c1c;border:1px solid #e53935;"
            "text-decoration:line-through;text-decoration-thickness:2px;"
            "font-weight:600;padding:0 2px;border-radius:2px;"
        )
    if kind == "replaced":
        return (
            "background-color:#e3f2fd;color:#0d47a1;border:1px solid #1e88e5;"
            "font-weight:600;padding:0 2px;border-radius:2px;"
        )
    return (
        "background-color:#e8f5e9;color:#1b5e20;border:1px solid #2e7d32;"
        "font-weight:600;padding:0 2px;border-radius:2px;"
    )


def heading_style(kind: str) -> str:
    if kind == "deleted":
        return "background-color:#ffebee;border-left:4px solid #e53935;padding-left:6px;text-decoration:line-through;"
    if kind == "replaced":
        return "background-color:#e3f2fd;border-left:4px solid #1e88e5;padding-left:6px;"
    return "background-color:#e8f5e9;border-left:4px solid #2e7d32;padding-left:6px;"


def image_wrapper_style(kind: str) -> str:
    if kind == "deleted":
        return "display:inline-block;outline:3px solid #e53935;border-radius:4px;padding:3px;opacity:0.7;"
    if kind == "replaced":
        return "display:inline-block;outline:3px solid #1e88e5;border-radius:4px;padding:3px;"
    return "display:inline-block;outline:3px solid #2e7d32;border-radius:4px;padding:3px;"


def image_tag_style(kind: str) -> str:
    if kind == "deleted":
        return "outline:3px solid #e53935;border-radius:4px;opacity:0.7;box-shadow:0 0 0 1px #e53935 inset;"
    if kind == "replaced":
        return "outline:3px solid #1e88e5;border-radius:4px;box-shadow:0 0 0 1px #1e88e5 inset;"
    return "outline:3px solid #2e7d32;border-radius:4px;box-shadow:0 0 0 1px #2e7d32 inset;"


def table_row_style(kind: str) -> str:
    if kind == "deleted":
        return "background-color:#ffebee; outline:2px solid #e53935; text-decoration:line-through; box-shadow:0 0 0 1px #e53935 inset;"
    if kind == "replaced":
        return "background-color:#e3f2fd; outline:2px solid #1e88e5; box-shadow:0 0 0 1px #1e88e5 inset;"
    return "background-color:#e8f5e9; outline:2px solid #2e7d32; box-shadow:0 0 0 1px #2e7d32 inset;"


def table_wrapper_style(kind: str) -> str:
    if kind == "deleted":
        return "display:block;outline:3px solid #e53935;background-color:#ffebee;border-radius:4px;padding:4px;opacity:0.85;"
    if kind == "replaced":
        return "display:block;outline:3px solid #1e88e5;background-color:#e3f2fd;border-radius:4px;padding:4px;"
    return "display:block;outline:3px solid #2e7d32;background-color:#e8f5e9;border-radius:4px;padding:4px;"


def reflect_preview_style(kind: str) -> str:
    if kind == "deleted":
        return "background-color:#ffebee;color:#b71c1c;border-left:3px solid #e53935;padding:4px 6px;margin:2px 0;"
    if kind == "replaced":
        return "background-color:#e3f2fd;color:#0d47a1;border-left:3px solid #1e88e5;padding:4px 6px;margin:2px 0;"
    return "background-color:#e8f5e9;color:#1b5e20;border-left:3px solid #2e7d32;padding:4px 6px;margin:2px 0;"


def cleanup_style_token_patterns() -> List[str]:
    return [
        r"\bdisplay\s*:\s*inline-block\s*;?",
        r"\boutline\s*:\s*[^;]*\s*;?",
        r"\bbox-shadow\s*:\s*[^;]*\s*;?",
        r"\bbackground-color\s*:\s*(?:#e3f2fd|#ffebee|#fff8e1|#e8f5e9|rgb\(\s*227\s*,\s*242\s*,\s*253\s*\)|rgb\(\s*255\s*,\s*235\s*,\s*238\s*\)|rgb\(\s*255\s*,\s*248\s*,\s*225\s*\)|rgb\(\s*232\s*,\s*245\s*,\s*233\s*\))\s*;?",
        r"\bcolor\s*:\s*(?:#0d47a1|#b71c1c|#8a6d00|#1b5e20|rgb\(\s*13\s*,\s*71\s*,\s*161\s*\)|rgb\(\s*183\s*,\s*28\s*,\s*28\s*\))\s*;?",
        r"\bborder(?:-left)?\s*:\s*[^;]*(?:#1e88e5|#e53935|#f9a825|#2e7d32|rgb\(\s*30\s*,\s*136\s*,\s*229\s*\)|rgb\(\s*229\s*,\s*57\s*,\s*53\s*\))[^;]*;?",
        r"\btext-decoration\s*:\s*line-through\s*;?",
        r"\btext-decoration-thickness\s*:\s*2px\s*;?",
        r"\bopacity\s*:\s*0\.7\s*;?",
        r"\bfont-weight\s*:\s*600\s*;?",
        r"\bpadding-left\s*:\s*6px\s*;?",
        r"\bborder-radius\s*:\s*4px\s*;?",
    ]
