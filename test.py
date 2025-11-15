import sys

try:
    import pyongc                                                                        	
    print("pyongc imported successfully")                                                 
except ImportError as e:                                                                 
    print(f"ImportError: {e}")                                                           
    import traceback                                                                     	
    traceback.print_exc()                                                                 
except Exception as e:                                                                   	
    print(f"An unexpected error occurred: {e}")                                           
    import traceback                                                                     	
    traceback.print_exc()