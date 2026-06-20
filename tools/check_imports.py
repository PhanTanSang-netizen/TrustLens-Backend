import importlib
import pkgutil
import sys
import traceback
from pathlib import Path


# Đưa thư mục backend vào sys.path để Python import được app/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


def main() -> None:
    try:
        import app
    except Exception as exc:
        print("❌ Cannot import app package.")
        print(f"Backend root: {BACKEND_ROOT}")
        print(f"Error: {type(exc).__name__}: {exc}")
        return

    errors: list[dict] = []
    total = 0

    print("🔍 Checking import errors in app/ ...")
    print(f"Backend root: {BACKEND_ROOT}")
    print("-" * 80)

    for module_info in pkgutil.walk_packages(app.__path__, prefix="app."):
        module_name = module_info.name
        total += 1

        try:
            importlib.import_module(module_name)
        except Exception as exc:
            errors.append(
                {
                    "module": module_name,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=10),
                }
            )

    print()
    print("=" * 80)
    print(f"Total modules checked: {total}")
    print(f"Total errors found: {len(errors)}")
    print("=" * 80)

    if not errors:
        print("✅ No import errors found.")
        return

    for index, error in enumerate(errors, start=1):
        print()
        print(f"[ERROR {index}]")
        print(f"Module     : {error['module']}")
        print(f"Error type : {error['error_type']}")
        print(f"Message    : {error['message']}")
        print("-" * 80)
        print(error["traceback"])
        print("=" * 80)

    output_path = BACKEND_ROOT / "check_imports_result.txt"

    with output_path.open("w", encoding="utf-8") as file:
        file.write(f"Backend root: {BACKEND_ROOT}\n")
        file.write(f"Total modules checked: {total}\n")
        file.write(f"Total errors found: {len(errors)}\n\n")

        for index, error in enumerate(errors, start=1):
            file.write(f"[ERROR {index}]\n")
            file.write(f"Module     : {error['module']}\n")
            file.write(f"Error type : {error['error_type']}\n")
            file.write(f"Message    : {error['message']}\n")
            file.write("-" * 80 + "\n")
            file.write(error["traceback"])
            file.write("\n" + "=" * 80 + "\n\n")

    print()
    print(f"📄 Saved result to: {output_path}")


if __name__ == "__main__":
    main()