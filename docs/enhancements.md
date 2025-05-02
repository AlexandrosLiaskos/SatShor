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