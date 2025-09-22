#!/usr/bin/env python3
"""Simple test to verify CLI commands work."""

import sys
from pathlib import Path

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cli_imports():
    """Test that CLI modules can be imported without errors."""
    print("🧪 Testing CLI Module Imports")
    print("=" * 30)
    
    try:
        from nhkprep.cli import app
        print("✅ CLI app imported successfully")
        
        # Test that original language imports work
        from nhkprep.original_lang import OriginalLanguageDetector
        print("✅ OriginalLanguageDetector imported")
        
        from nhkprep.original_lang.config import OriginalLanguageConfig  
        print("✅ OriginalLanguageConfig imported")
        
        # Test config creation
        config = OriginalLanguageConfig(cache_enabled=False)
        print("✅ Config creation works")
        
        # Test detector creation  
        detector = OriginalLanguageDetector(config)
        print("✅ Detector creation works")
        
        print("\n🎉 All CLI imports working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_cli_help():
    """Test that CLI help can be displayed."""
    print("\n🧪 Testing CLI Help")
    print("=" * 20)
    
    try:
        import subprocess
        import sys
        
        # Run the CLI with --help
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; sys.path.insert(0, 'src'); "
            "from nhkprep.cli import app; "
            "try: app(['--help']); "
            "except SystemExit: print('Help displayed successfully')"
        ], capture_output=True, text=True, timeout=10)
        
        if "Help displayed successfully" in result.stdout or "NHK" in result.stdout:
            print("✅ CLI help works")
            return True
        else:
            print(f"❌ CLI help issue: {result.stdout} {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ CLI help error: {e}")
        return False

if __name__ == "__main__":
    success1 = test_cli_imports()
    success2 = test_cli_help()
    
    if success1 and success2:
        print("\n🎉 CLI Integration Test: PASSED")
    else:
        print("\n❌ CLI Integration Test: FAILED")
        sys.exit(1)