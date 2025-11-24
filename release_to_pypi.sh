#!/bin/bash
set -e

echo "Preparing cai-framework for PyPI release..."


# Install required build tools without upgrading pip
# pip install --upgrade pip setuptools wheel twine build
pip install setuptools wheel twine build

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: pyproject.toml is missing"
    exit 1
fi


# Check if README.md exists
if [ ! -f "README.md" ]; then
    echo "ERROR: README.md is missing"
    exit 1
fi

# Clean previous builds
rm -rf build/ dist/ *.egg-info/ .eggs/
# Also clean any cached build files
rm -rf src/*.egg-info/

# Build the package
echo "Building package..."
python3 -m build

# Check the package
echo "Running twine check..."
twine check dist/*

echo ""
echo "Package is ready for upload!"
echo ""
echo "To upload to TestPyPI (recommended for testing):"
echo "twine upload --repository testpypi dist/*"
echo ""
echo "To upload to PyPI (production):"
echo "twine upload dist/*"
echo ""
echo "After uploading to TestPyPI, you can install with:"
echo "pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple cai-framework"
echo ""
echo "To test in a clean environment:"
echo "python3 -m venv test_env"
echo "source test_env/bin/activate"
echo "pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple cai-framework"
