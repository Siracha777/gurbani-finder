import os
import toml

# Path to your Gurbani database lines folder
BASE_PATH = r"C:\Users\Satbir\gurbani-app\database_main\database-main\collections\lines"

def count_gurbani_lines(base_path=BASE_PATH):
    total_lines = 0
    file_count = 0

    for root, dirs, files in os.walk(base_path):
        for file in sorted(files):
            if file.endswith(".toml"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = toml.load(f)

                        if "content" in data:
                            # Count how many primary (Gurmukhi) lines exist
                            for block in data["content"]:
                                if block["type"] == "primary":
                                    total_lines += 1

                    file_count += 1

                except Exception as e:
                    print(f"❌ Error in {file_path}: {e}")

    print(f"✅ Processed {file_count} files")
    print(f"📊 Total Gurbani lines found: {total_lines}")

if __name__ == "__main__":
    count_gurbani_lines()
