import os
import subprocess
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_build():
    """Run Pygbag build for web output."""
    logger.info("Starting Pygbag build for web")
    build_dir = "src/build/web"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        logger.info(f"Cleared existing build directory: {build_dir}")
    
    # Run Pygbag with explicit web template
    cmd = ["python", "-m", "pygbag", "--build", "src", "--template", "WEB"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info(f"Pygbag stdout: {result.stdout}")
    if result.stderr:
        logger.error(f"Pygbag stderr: {result.stderr}")
    
    # Verify build output
    if os.path.exists(build_dir):
        logger.info(f"Build output created at {build_dir}")
        for root, _, files in os.walk(build_dir):
            for file in files:
                logger.info(f"Found file: {os.path.join(root, file)}")
    else:
        logger.error(f"Build directory {build_dir} not found")
        raise FileNotFoundError(f"Build directory {build_dir} not created")

if __name__ == "__main__":
    try:
        run_build()
    except Exception as e:
        logger.error(f"Build failed: {e}")
        raise