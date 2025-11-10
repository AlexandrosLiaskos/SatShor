# Implemented Enhancements

## OCAS - Optimal Coverage Acquisition System (Implemented)

The OCAS feature has been successfully implemented to solve the **Satellite Image Mosaic Selection Problem (SIMSP)** - a geometric set cover optimization problem.

### Implementation Overview

OCAS provides two approaches for selecting a minimal set of satellite images that completely cover a geographic area:

1. **Greedy Heuristic (`coverage_greedy`)**: Fast, near-optimal solution
   - Iteratively selects images with best marginal coverage gain per cost
   - Typically within 10-20% of optimal solution
   - Suitable for large areas (>1000 km²)
   - Runtime: O(n²) where n is number of candidates

2. **MILP-Based Optimal (`coverage_optimal`)**: Globally optimal solution
   - Uses OR-Tools pywraplp to solve binary integer program
   - Guarantees minimal number of images for complete coverage
   - Best for small-medium areas (<500 km²)
   - May be slow for large problems (>100 candidates)

### Key Features

- **Point Sampling Approach**: Discretizes AOI into uniform grid of sample points
- **Coverage Matrix**: Precomputes point-in-polygon tests for efficiency
- **Weighted Cost Function**: Balances cloud cover and quality score
- **Configurable Parameters**: Grid spacing, coverage tolerance, solver timeout
- **Graceful Degradation**: Falls back to greedy if MILP solver fails or times out

### Files Modified/Created

- **Implementation**: `src/image_collector/coverage_optimizer.py`
- **Configuration**: `src/image_collector/config_schema.py`
- **Integration**: `src/image_collector/collection_core.py`, `src/image_collector/collector.py`
- **Documentation**: `src/image_collector/README.md`, `README.md`
- **Examples**: `src/image_collector/config.example.yaml`

### Relation to P vs NP

The set cover problem is NP-complete, meaning:
- No known polynomial-time algorithm exists for finding the optimal solution
- The greedy heuristic provides a logarithmic approximation guarantee
- The MILP approach finds the optimal solution but may take exponential time in worst case
- SatShor implements both the pragmatic (greedy) and optimal (MILP) paths as originally envisioned

### Usage

See `src/image_collector/README.md` for comprehensive usage examples and performance considerations.

---

# Future Enhancements

# Additional usage of B08A (865nm, bandwidth 20nm)


```python
def enhanced_water_detection(b8_data, b8a_data=None):
    """
    Enhanced water detection leveraging the ~889nm absorption peak of water.
    
    Args:
        b8_data: Band 8 (NIR) data
        b8a_data: Band 8A data (optional, would need to be resampled to match B8 resolution)
    """
    if b8a_data is not None:
        # Create weighted combination to target ~889nm absorption peak
        # Weights based on proximity to 889nm and bandwidth
        weight_b8 = 0.6  # Band 8 covers 784.5-899.5nm (includes 889nm)
        weight_b8a = 0.4  # Band 8A centered at 865nm (closer to 889nm)
        combined_band = (weight_b8 * b8_data + weight_b8a * b8a_data) / (weight_b8 + weight_b8a)
    else:
        combined_band = b8_data
    
    # Apply physics-based thresholding targeting water's low reflectance at ~889nm
    # This could be more sophisticated than the current minimum threshold
    water_threshold = estimate_water_threshold(combined_band)
    binary_mask = combined_band <= water_threshold
    
    return binary_mask, water_threshold
```