from executor_service.trade_logger import trade_logger

def verify():
    print("TESTING HISTORY HYDRATION...")
    try:
        trade_logger.hydrate_history()
        print("✅ Hydration Routine Completed.")
    except Exception as e:
        print(f"❌ Hydration Failed: {e}")

if __name__ == "__main__":
    verify()
