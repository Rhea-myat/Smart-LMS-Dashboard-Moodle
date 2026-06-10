# test write log 
from etl_test import write_log, load_data

if __name__ == "__main__":
    write_log("Starting test of write_log function.")
    try: 
        write_log("This is a test log entry.")
        print("write_log function works correctly.")
    except Exception as e: 
        print(f"Error in write_log function: {e}")