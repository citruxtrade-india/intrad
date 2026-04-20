from pya3 import Aliceblue
try:
    a = Aliceblue('u', 'a')
    # Try all common private base url attributes
    urls = {
        "_base_url": getattr(a, "_base_url", "N/A"),
        "base_url": getattr(a, "base_url", "N/A"),
        "_Aliceblue__base_url": getattr(a, "_Aliceblue__base_url", "N/A"),
    }
    print(urls)
except Exception as e:
    print(f"Error: {e}")
