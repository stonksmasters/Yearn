import os
import shutil
import subprocess

# Run Pygbag
subprocess.run(["python", "-m", "pygbag", "--build", "src"])

# Move build output to build/web
src_dir = "src/build/web"
dest_dir = "build/web"
if os.path.exists(src_dir):
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.move(src_dir, dest_dir)
    print(f"Moved build output to {dest_dir}")