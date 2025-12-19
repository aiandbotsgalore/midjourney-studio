"""
Script to remove duplicate code from app.py (lines 401-846).
"""

def cleanup_app_py():
    """Remove duplicate old API class and utility functions."""

    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"Original file: {len(lines)} lines")

    # Keep lines 1-400 (index 0-399)
    # Skip lines 401-846 (index 400-845)
    # Keep lines 847+ (index 846+)
    new_lines = lines[:400] + lines[846:]

    print(f"After cleanup: {len(new_lines)} lines")
    print(f"Removed {len(lines) - len(new_lines)} lines")

    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print("\n✅ Successfully removed duplicate code (lines 401-846)")
    print("✅ app.py cleaned up!")

if __name__ == "__main__":
    cleanup_app_py()
