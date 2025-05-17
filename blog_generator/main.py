import importlib.util
from core.utils import bcolors

ENABLE_RETRIES = False

def load_and_run_generate():
    spec = importlib.util.spec_from_file_location("generate_landing_pages", "./scripts/generate_landing_pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()

def load_and_run_retry():
    spec = importlib.util.spec_from_file_location("retry_failed_blogs", "./scripts/retry_failed_blogs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()

def run_full_pipeline():
    print(f"{bcolors.HEADER}🚀 Starting Full Blog Generation Pipeline...{bcolors.ENDC}")

    print(f"{bcolors.OKBLUE}🔵 Step 1: Generating new blogs from scripts/...{bcolors.ENDC}")
    load_and_run_generate()

    if ENABLE_RETRIES:
        print(f"\n{bcolors.WARNING}🟡 Step 2: Retrying failed blogs (if needed)...{bcolors.ENDC}")
        load_and_run_retry()

    print(f"\n{bcolors.OKGREEN}🏁 All Done! Blogs generated and retried.{bcolors.ENDC}")

if __name__ == "__main__":
    run_full_pipeline()
