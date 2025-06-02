#!/usr/bin/env python3
"""
Test script to verify JSON serialization fix
"""

import sys
import os
import json
sys.path.append('src/logbook')

try:
    from app import LogbookEntry
    from datetime import datetime
    
    print("✅ Import successful")
    
    # Test LogbookEntry to_dict conversion
    entry = LogbookEntry(entry_id=1, title="Test Entry", content="Test content")
    entry_dict = entry.to_dict()
    print(f"✅ Entry to_dict: {entry_dict}")
    
    # Test JSON serialization
    json_str = json.dumps(entry_dict)
    print(f"✅ JSON serialization successful: {len(json_str)} characters")
    
    # Test list of entries
    entries = [
        LogbookEntry(entry_id=1, title="Entry 1", content="Content 1"),
        LogbookEntry(entry_id=2, title="Entry 2", content="Content 2")
    ]
    
    entries_data = [entry.to_dict() for entry in entries]
    json_list = json.dumps(entries_data)
    print(f"✅ List JSON serialization successful: {len(json_list)} characters")
    
    print("\n🎉 JSON serialization fix verified!")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()