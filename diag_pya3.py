
import pya3
import datetime
import inspect

try:
    print(f"pya3 version: {getattr(pya3, '__version__', 'unknown')}")
    import pya3.alicebluepy
    print(f"pya3.alicebluepy.time: {pya3.alicebluepy.time}")
    print(f"Is callable? {callable(pya3.alicebluepy.time)}")
    
    # Try to reproduce the error
    try:
        pya3.alicebluepy.time(8, 0)
        print("Success calling time(8, 0)")
    except Exception as e:
        print(f"Error calling time(8, 0): {e}")
        
except Exception as e:
    print(f"Diagnostic failed: {e}")
