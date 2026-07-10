import json
import re
import sys

BLOCKED_PATTERNS = [
    r"data[\\/]ryohi\.db$",
    r"\.streamlit[\\/]secrets\.toml$",
]


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    if any(re.search(pattern, file_path) for pattern in BLOCKED_PATTERNS):
        message = (
            f"{file_path} は実データ/認証情報が入っているため、"
            "Claude Codeからの読み書きをブロックしています。"
        )
        print(json.dumps({
            "hookSpecificOutput": {"permissionDecision": "deny"},
            "systemMessage": message,
        }), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
