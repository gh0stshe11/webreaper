"""Tests for raw_store resume behavior."""
import json
import pytest
from pathlib import Path
from webreaper.storage.raw_store import RawStore


def test_raw_store_save_load(tmp_path):
    """Test saving and loading raw data."""
    store = RawStore(tmp_path)
    
    # Save data
    data = ["url1", "url2", "url3"]
    filepath = store.save("test", data)
    
    # Check file exists
    assert filepath.exists()
    assert filepath.name == "raw_test.json"
    
    # Load data
    loaded = store.load("test")
    assert loaded == data


def test_raw_store_exists(tmp_path):
    """Test exists method."""
    store = RawStore(tmp_path)
    
    # Initially doesn't exist
    assert not store.exists("nonexistent")
    
    # Save and check exists
    store.save("test", ["data"])
    assert store.exists("test")


def test_raw_store_should_skip_resume_true(tmp_path):
    """Test should_skip with resume=True."""
    store = RawStore(tmp_path)
    
    # No file exists - should not skip
    assert not store.should_skip("test", resume=True)
    
    # File exists - should skip
    store.save("test", ["data"])
    assert store.should_skip("test", resume=True)


def test_raw_store_should_skip_resume_false(tmp_path):
    """Test should_skip with resume=False."""
    store = RawStore(tmp_path)
    
    # File exists but resume=False - should not skip
    store.save("test", ["data"])
    assert not store.should_skip("test", resume=False)


def test_raw_store_load_nonexistent(tmp_path):
    """Test loading nonexistent file."""
    store = RawStore(tmp_path)
    
    result = store.load("nonexistent")
    assert result is None


def test_raw_store_load_invalid_json(tmp_path):
    """Test loading invalid JSON file."""
    store = RawStore(tmp_path)
    
    # Create invalid JSON file
    filepath = tmp_path / "raw_invalid.json"
    filepath.write_text("not valid json{{{")
    
    result = store.load("invalid")
    assert result is None


def test_raw_store_complex_data(tmp_path):
    """Test saving and loading complex data structures."""
    store = RawStore(tmp_path)
    
    data = {
        "urls": ["http://example.com/1", "http://example.com/2"],
        "metadata": {
            "count": 2,
            "source": "test"
        }
    }
    
    store.save("complex", data)
    loaded = store.load("complex")
    
    assert loaded == data
    assert loaded["urls"] == data["urls"]
    assert loaded["metadata"]["count"] == 2


def test_raw_store_creates_directory(tmp_path):
    """Test that RawStore creates output directory."""
    out_dir = tmp_path / "output" / "nested"
    store = RawStore(out_dir)
    
    # Directory should be created
    assert out_dir.exists()
    assert out_dir.is_dir()
