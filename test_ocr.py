import pytesseract
from PIL import Image
import os

def test_ocr():
    print("🧪 Testing OCR functionality...")
    
    # Test 1: Check if Tesseract is accessible
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
    except Exception as e:
        print(f"❌ Tesseract not found: {e}")
        print("\n💡 Installation instructions:")
        print("1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Run the Windows installer")
        print("3. Make sure to check 'Add to PATH' during installation")
        print("4. Restart VS Code after installation")
        return False
    
    # Test 2: Create a simple test image with text
    try:
        # Create a simple image with text for testing
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a blank image
        img = Image.new('RGB', (400, 200), color='white')
        d = ImageDraw.Draw(img)
        
        # Try to use a basic font
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Draw text
        d.text((10, 10), "This is a test for OCR functionality.", fill='black', font=font)
        d.text((10, 50), "The Second Brain should read this text.", fill='black', font=font)
        d.text((10, 90), "Hello from your AI assistant!", fill='black', font=font)
        
        test_image_path = "test_ocr_image.png"
        img.save(test_image_path)
        print(f"✅ Created test image: {test_image_path}")
        
        # Test 3: Try OCR on the test image
        extracted_text = pytesseract.image_to_string(img)
        print("✅ OCR Test Results:")
        print("Extracted Text:")
        print("-" * 40)
        print(extracted_text)
        print("-" * 40)
        
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            
        return True
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

if __name__ == "__main__":
    test_ocr()