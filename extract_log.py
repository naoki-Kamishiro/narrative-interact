"""tools/extract_log.py を narrative-interact の直下から呼ぶための入口（中身は tools/extract_log.py）"""
import os
import runpy
import sys

sys.argv[0] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "extract_log.py")
runpy.run_path(sys.argv[0], run_name="__main__")
