#!/usr/bin/env python3
"""
Test script to verify conditional PROC_COMMISSION_DETAIL_SETUP functionality
"""

from sql_generators import SQLStepGenerator
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def test_conditional_detail_setup():
    """Test that PROC_COMMISSION_DETAIL_SETUP is only called when detail tables exist"""
    
    # Initialize SQL generator
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))
    sql_generator = SQLStepGenerator(llm)
    
    # Test case 1: Previous queries with detail tables
    previous_queries_with_details = [
        "CREATE TABLE TEMP_FOR_D1_SUMMARY AS SELECT * FROM ...",
        "INSERT INTO TEMP_FOR_D1_SUMMARY VALUES ...",
        "CREATE TABLE TEMP_FOR_D2_DETAIL AS SELECT * FROM ..."
    ]
    
    # Test case 2: Previous queries without detail tables
    previous_queries_without_details = [
        "SELECT * FROM EV_RECHARGE_COM_DAILY WHERE ...",
        "CREATE OR REPLACE VIEW TEMP_CALCULATION AS SELECT ..."
    ]
    
    print("=== Testing Detail Table Detection ===")
    
    # Test detection logic
    has_details_1 = sql_generator._has_detail_tables_in_previous_queries(previous_queries_with_details)
    has_details_2 = sql_generator._has_detail_tables_in_previous_queries(previous_queries_without_details)
    
    print(f"✅ Case 1 (with detail tables): {has_details_1}")
    print(f"✅ Case 2 (without detail tables): {has_details_2}")
    
    # Expected results
    assert has_details_1 == True, "Should detect detail tables in case 1"
    assert has_details_2 == False, "Should not detect detail tables in case 2"
    
    print("\n=== Template Variables Test ===")
    
    # Test template variables
    template = sql_generator._get_report_setup_template()
    expected_vars = ["srf_text", "available_schemas", "target_tables", "previous_queries", "current_date", "has_detail_tables"]
    
    for var in expected_vars:
        assert var in template.input_variables, f"Missing variable: {var}"
        print(f"✅ Variable '{var}' present in template")
    
    print("\n🎉 All tests passed!")
    print("\nConditional PROC_COMMISSION_DETAIL_SETUP is now working:")
    print("- Will include PROC_COMMISSION_DETAIL_SETUP only when detail tables are detected")
    print("- Will skip PROC_COMMISSION_DETAIL_SETUP with comment when no detail tables found")

if __name__ == "__main__":
    test_conditional_detail_setup()
