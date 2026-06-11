"""
Unit tests for the expert hara helper function process_hara_properties.
"""
from typing import Any
import pytest
from app.api.expert import process_hara_properties


def test_process_hara_properties_maps_null_to_sentinel() -> None:
    """
    Ensure that None/null values for key soil nutrients and pH
    are mapped to the sentinel value -9999.0.
    """
    input_data: dict[str, Any] = {
        "ph_rata2": None,
        "n_rata2": None,
        "p_rata2": None,
        "k_rata2": None,
        "name": "Area test",
        "slope__": "0-8",
    }
    
    result = process_hara_properties(input_data)
    
    assert result["ph_rata2"] == -9999.0
    assert result["n_rata2"] == -9999.0
    assert result["p_rata2"] == -9999.0
    assert result["k_rata2"] == -9999.0
    assert result["name"] == "Area test"
    assert result["slope__"] == "0-8"


def test_process_hara_properties_scales_potassium_below_100() -> None:
    """
    Ensure that Potassium (k_rata2) values below 100.0 (excluding sentinel -9999)
    are multiplied by 10.0 before DB insertion.
    """
    input_data: dict[str, Any] = {
        "k_rata2": 15.4,
        "ph_rata2": 6.5,
    }
    
    result = process_hara_properties(input_data)
    
    assert result["k_rata2"] == 154.0
    assert result["ph_rata2"] == 6.5


def test_process_hara_properties_does_not_scale_potassium_above_100() -> None:
    """
    Ensure that Potassium (k_rata2) values of 100.0 or higher are not scaled.
    """
    input_data: dict[str, Any] = {
        "k_rata2": 150.0,
    }
    
    result = process_hara_properties(input_data)
    
    assert result["k_rata2"] == 150.0


def test_process_hara_properties_leaves_other_values_unmodified() -> None:
    """
    Ensure other keys and nutrient values are not modified.
    """
    input_data: dict[str, Any] = {
        "ph_rata2": 5.5,
        "n_rata2": 2.4,
        "p_rata2": 12.0,
    }
    
    result = process_hara_properties(input_data)
    
    assert result["ph_rata2"] == 5.5
    assert result["n_rata2"] == 2.4
    assert result["p_rata2"] == 12.0
