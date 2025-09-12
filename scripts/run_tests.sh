#!/bin/bash
# Test runner script for QA MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="unit"
VERBOSE=false
COVERAGE=false
PARALLEL=false
MARKERS=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: unit, integration, all (default: unit)"
    echo "  -v, --verbose          Verbose output"
    echo "  -c, --coverage         Run with coverage report"
    echo "  -p, --parallel         Run tests in parallel"
    echo "  -m, --markers MARKERS  Pytest markers to run (e.g., 'not slow')"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run unit tests"
    echo "  $0 -t integration                     # Run integration tests"
    echo "  $0 -t all -c                         # Run all tests with coverage"
    echo "  $0 -m 'not slow'                     # Run tests excluding slow ones"
    echo "  $0 -t integration -m smoke           # Run integration smoke tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate test type
if [[ ! "$TEST_TYPE" =~ ^(unit|integration|all)$ ]]; then
    print_error "Invalid test type: $TEST_TYPE. Must be unit, integration, or all."
    exit 1
fi

# Change to project directory
cd "$(dirname "$0")/.."

print_status "Starting QA MCP Server tests..."
print_status "Test type: $TEST_TYPE"
print_status "Verbose: $VERBOSE"
print_status "Coverage: $COVERAGE"
print_status "Parallel: $PARALLEL"
if [[ -n "$MARKERS" ]]; then
    print_status "Markers: $MARKERS"
fi

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_warning "Virtual environment not detected. Consider activating it first."
fi

# Install test dependencies if needed
if [[ ! -f "tests/requirements-test.txt" ]]; then
    print_error "Test requirements file not found: tests/requirements-test.txt"
    exit 1
fi

print_status "Installing test dependencies..."
pip install -r tests/requirements-test.txt

# Build pytest command
PYTEST_CMD="pytest"

# Add test paths based on type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests/"
        ;;
esac

# Add markers if specified
if [[ -n "$MARKERS" ]]; then
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

# Add verbose flag
if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage if requested
if [[ "$COVERAGE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term-missing"
fi

# Add parallel execution if requested
if [[ "$PARALLEL" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Add additional options
PYTEST_CMD="$PYTEST_CMD --tb=short --strict-markers"

print_status "Running command: $PYTEST_CMD"

# Run tests
if eval $PYTEST_CMD; then
    print_success "All tests passed!"
    
    if [[ "$COVERAGE" == true ]]; then
        print_status "Coverage report generated in htmlcov/index.html"
    fi
    
    exit 0
else
    print_error "Some tests failed!"
    exit 1
fi
