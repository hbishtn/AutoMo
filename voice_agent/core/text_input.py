"""
Text-input mode: type commands instead of speaking them.
"""


def get_text_command() -> str:
    try:
        return input("Aap (type karo): ").strip()
    except EOFError:
        return ""