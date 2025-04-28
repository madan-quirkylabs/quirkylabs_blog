"""
retry_utils.py

Purpose:
    Provides a reusable decorator for automatic retries
    with exponential backoff and jitter.

Use Cases:
    - Retrying unreliable API calls (e.g., OpenAI, Google APIs)
    - Fault tolerance for network operations
    - Production-grade reliability

Author: QuirkyLabs
"""

import time
import random
import functools

def retry_with_exponential_backoff(
    max_retries=5,
    initial_backoff=2,
    max_backoff=60,
    allowed_exceptions=(Exception,),
    logger=None
):
    """
    Decorator to retry a function with exponential backoff and jitter.

    Args:
        max_retries (int): Maximum number of retries allowed.
        initial_backoff (float): Initial delay in seconds.
        max_backoff (float): Maximum delay between retries.
        allowed_exceptions (tuple): Exceptions that should trigger a retry.
        logger (LoggerManager, optional): Custom structured logger.

    Returns:
        function: Wrapped function with retry mechanism.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0

            while True:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    retries += 1

                    if retries > max_retries:
                        error_msg = (
                            f"[RetryUtils] ❌ Maximum retries exceeded for '{func.__name__}' "
                            f"after {max_retries} attempts. Raising exception."
                        )
                        if logger:
                            logger.error(error_msg, extra={"exception": str(e)})
                        else:
                            print(error_msg)
                        raise

                    # Exponential backoff with jitter
                    backoff = min(initial_backoff * (2 ** (retries - 1)), max_backoff)
                    jitter = random.uniform(0, 1)
                    sleep_time = backoff + jitter

                    warning_msg = (
                        f"[RetryUtils] ⚡ Exception in '{func.__name__}': {str(e)} | "
                        f"Retrying in {sleep_time:.2f} seconds (attempt {retries}/{max_retries})"
                    )

                    if logger:
                        logger.warning(warning_msg)
                    else:
                        print(warning_msg)

                    time.sleep(sleep_time)

        return wrapper
    return decorator

# --- Example Usage (Only for local testing) ---

if __name__ == "__main__":
    from utils.logger_manager import LoggerManager

    logger = LoggerManager()

    @retry_with_exponential_backoff(max_retries=3, initial_backoff=1, logger=logger)
    def flaky_operation():
        print("🚀 Attempting risky operation...")
        if random.random() < 0.8:
            raise ValueError("Random simulated failure!")
        return "🎯 Success!"

    try:
        result = flaky_operation()
        print(result)
    except Exception as e:
        print(f"❌ Final failure: {str(e)}")
