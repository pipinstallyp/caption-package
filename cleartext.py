import os
import sys
import glob

def delete_txt_files(dir_path):
    # Validate if the given directory exists
    if not os.path.exists(dir_path):
        print(f"Directory '{dir_path}' does not exist.")
        return

    # Get all the files with '.txt' extension in the given directory
    txt_files = glob.glob(os.path.join(dir_path, '*.txt'))

    if not txt_files:
        print(f"No '.txt' files found in the directory '{dir_path}'.")
        return

    # Delete the txt files
    for file in txt_files:
        try:
            os.remove(file)
            print(f"Deleted '{file}'.")
        except Exception as e:
            print(f"Error deleting '{file}': {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cleartext.py <directory>")
        sys.exit(1)

    dir_path = sys.argv[1]
    delete_txt_files(dir_path)