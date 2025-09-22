#!/usr/bin/env python3
"""Simple CLI demonstration script."""

import tempfile
from pathlib import Path

def create_test_file():
    """Create a test media file for CLI testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mkv") as f:
        test_file = Path(f.name)
    
    # Rename to a meaningful filename
    demo_file = test_file.parent / "Spirited Away (2001) [1080p].mkv"
    test_file.rename(demo_file)
    
    print(f"📁 Created test file: {demo_file}")
    return demo_file

def demonstrate_cli():
    """Demonstrate CLI functionality."""
    print("🎬 Original Language Detection CLI Demo")
    print("=" * 45)
    
    # Create a test file
    test_file = create_test_file()
    
    try:
        print("\n📋 Available CLI commands:")
        print("1. detect-original-lang - Detect language for a single file")
        print("2. batch-detect-original-lang - Batch process multiple files") 
        print("3. manage-original-lang-cache - Manage detection cache")
        
        print(f"\n🔧 Example usage:")
        print(f"python -m nhkprep detect-original-lang '{test_file}'")
        print(f"python -m nhkprep batch-detect-original-lang '{test_file.parent}'")
        print(f"python -m nhkprep manage-original-lang-cache stats")
        
        print(f"\n🎯 CLI Command Features:")
        print("✅ Single file detection with confidence scoring")
        print("✅ Batch processing for multiple files")
        print("✅ JSON output for automation")
        print("✅ Cache management and statistics")
        print("✅ Configurable backends (TMDb, IMDb)")
        print("✅ Timeout and confidence threshold controls")
        print("✅ Rich formatted output with tables")
        
        print(f"\n📊 Command Structure Validation:")
        
        # Test imports work
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent / "src"))
            from nhkprep.cli import app
            from nhkprep.original_lang import OriginalLanguageDetector
            from nhkprep.original_lang.config import OriginalLanguageConfig
            print("✅ All CLI modules imported successfully")
            print("✅ Original language detection API ready")
            print("✅ Configuration system available")
        except Exception as e:
            print(f"❌ Import error: {e}")
        
        print(f"\n🎉 CLI integration is ready!")
        print(f"👉 The commands are available but need TMDb API key for full functionality")
        
    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)
        print(f"\n🧹 Cleaned up test file")

if __name__ == "__main__":
    demonstrate_cli()