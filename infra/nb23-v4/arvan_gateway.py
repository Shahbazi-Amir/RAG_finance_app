"""Explicit response compatibility for the pinned Arvan C340 request."""

def metadata_issues(doc, message, usage, profile):
    expected = profile["model"]
    returned = doc.get("model")
    arvan_flash = (expected == "DeepSeek-V4-Flash"
                   and returned in (expected, "deepseek/deepseek-v4-flash"))
    issues = []
    if returned != expected and not arvan_flash:
        issues.append("RETURNED_MODEL_REVIEW")

    details = usage.get("completion_tokens_details", {})
    if not isinstance(details, dict):
        return issues + ["REASONING_MISSING_OR_NONZERO"]
    reported = [container["reasoning_tokens"] for container in (details, usage)
                if "reasoning_tokens" in container]
    omission_allowed = arvan_flash and profile.get("thinking") == {"type": "disabled"}
    if (any(type(value) is not int or value != 0 for value in reported)
            or not (reported or omission_allowed)
            or (omission_allowed and any(
                message.get(key) not in (None, "")
                for key in ("reasoning", "reasoning_content", "reasoning_details")))):
        issues.append("REASONING_MISSING_OR_NONZERO")
    return issues

def overlay_generation(source):
    """Apply only to the verified upstream text and require exact patch anchors."""
    replacements = {
        "def generate(root, outputs, source, request_id):":
            "def generate(root, outputs, source, request_id, *, diagnostic_root, gateway_settings):",
        '(root / ".env").read_text(encoding="utf-8-sig")':
            'gateway_settings.read_text(encoding="utf-8-sig")',
        'outputs.glob("C028_one_diagnostic_*/C028.summary.*.json")':
            'diagnostic_root.glob("C028_one_diagnostic_*/C028.summary.*.json")',
        '    issues = []\n    if doc.get("model") != profile["model"]:\n'
        '        issues.append("RETURNED_MODEL_REVIEW")':
            "    issues = metadata_issues(doc, message, usage, profile)",
        '    details = usage.get("completion_tokens_details")\n'
        '    reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None\n'
        '    if reasoning is None:\n        reasoning = usage.get("reasoning_tokens")\n': "",
        '    if type(reasoning) is not int or reasoning != 0:\n'
        '        issues.append("REASONING_MISSING_OR_NONZERO")\n': "",
    }
    for original, replacement in replacements.items():
        if source.count(original) != 1:
            raise ValueError("ARVAN_ENGINE_OVERLAY_ANCHOR_MISMATCH")
        source = source.replace(original, replacement, 1)
    return source
