#!/usr/bin/env python3
"""
Test script to verify enhanced metadata extraction with detail table detection
"""

from sql_generators import MetadataExtractor
from langchain_openai import ChatOpenAI
from models import CommissionState
import os
from dotenv import load_dotenv

load_dotenv()

def test_metadata_detail_table_detection():
    """Test that metadata extraction correctly detects detail table requirements"""
    
    # Initialize metadata extractor
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))
    metadata_extractor = MetadataExtractor(llm)
    
    # Test case 1: SRF with detail table specifications
    srf_with_details = """
    Commission Name: Test Campaign with Details
    Start Date: 10-Aug-2024
    End Date: 15-Aug-2024
    Commission Receiver Channel: Distributor
    
    Detail Format:
    Detail 1 (Summary Level):
    - Table: TEMP_FOR_D1_SUMMARY
    - Columns: DD_CODE, REGION, TOTAL_AMOUNT, COMMISSION
    
    Detail 2 (Transaction Level):
    - Table: TEMP_FOR_D2_TRANSACTIONS  
    - Columns: DD_CODE, MSISDN, AMOUNT, DATE, COMMISSION
    
    Expected Output Tables:
    Create the above detail tables with specified column structure.
    """
    
    # Test case 2: SRF without detail table specifications
    srf_without_details = """
    Commission Name: Simple Campaign
    Start Date: 10-Aug-2024
    End Date: 15-Aug-2024
    Commission Receiver Channel: Distributor
    
    Commission Business Logic:
    - Calculate recharge commission for distributors
    - Apply 5% commission rate
    - No specific output format required
    """
    
    print("=== Testing Enhanced Metadata Extraction ===")
    
    # Test case 1: With detail tables
    state1 = CommissionState(
        srf_text=srf_with_details,
        table_schemas={},
        metadata=None,
        sql_steps=[],
        errors=[],
        warnings=[],
        final_script=None,
        summary_report=None
    )
    
    result1 = metadata_extractor.extract(state1)
    metadata1 = result1["metadata"]
    
    print(f"✅ Case 1 (with detail specs):")
    print(f"   Commission Name: {metadata1.get('commission_name')}")
    print(f"   Has Detail Tables: {metadata1.get('has_detail_tables')}")
    
    # Test case 2: Without detail tables
    state2 = CommissionState(
        srf_text=srf_without_details,
        table_schemas={},
        metadata=None,
        sql_steps=[],
        errors=[],
        warnings=[],
        final_script=None,
        summary_report=None
    )
    
    result2 = metadata_extractor.extract(state2)
    metadata2 = result2["metadata"]
    
    print(f"✅ Case 2 (without detail specs):")
    print(f"   Commission Name: {metadata2.get('commission_name')}")
    print(f"   Has Detail Tables: {metadata2.get('has_detail_tables')}")
    
    # Validate results
    assert metadata1.get('has_detail_tables') == True, "Should detect detail tables in case 1"
    assert metadata2.get('has_detail_tables') == False, "Should not detect detail tables in case 2"
    
    print("\n🎉 Enhanced Metadata Extraction Tests Passed!")
    print("\nBenefits of this enhancement:")
    print("✅ Detail table detection moved to metadata extraction phase")
    print("✅ Consistent decision-making across all workflow steps")
    print("✅ Eliminates redundant SRF analysis in multiple places")
    print("✅ Metadata-driven workflow reduces complexity")
    print("✅ Single source of truth for detail table requirements")

if __name__ == "__main__":
    test_metadata_detail_table_detection()
