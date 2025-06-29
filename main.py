import os
import asyncio

if __name__ == "__main__":
    try:
        from src.main import main

        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\nThe program has exited.")
    except Exception as e:
        print(f"error：{e}")
    finally:
        os.system("pause")
