#!/usr/bin/env python3
"""
Test script for file upload functionality
"""

import os
import sys
import pandas as pd

def create_sample_files():
    """Create sample CSV and Excel files for testing"""
    
    # Sample data for testing
    sample_data = {
        'Cluster Name': ['North', 'South', 'East', 'West'],
        'REGION': ['Region1', 'Region2', 'Region3', 'Region4'],
        'DD_CODE': ['DD001', 'DD002', 'DD003', 'DD004'],
        'DD Name': ['Distributor A', 'Distributor B', 'Distributor C', 'Distributor D'],
        'SELECTED_REC_TARGET': [10000, 15000, 12000, 18000],
        'SELECTED_REC_INCENTIVE': [500, 750, 600, 900],
        'All_Bundle_Target': [25000, 35000, 28000, 40000]
    }
    
    df = pd.DataFrame(sample_data)
    
    # Create test files directory
    os.makedirs('test_files', exist_ok=True)
    
    # Save as CSV
    df.to_csv('test_files/target_table_data.csv', index=False)
    print("✅ Created: test_files/target_table_data.csv")
    
    # Save as Excel
    df.to_excel('test_files/target_table_data.xlsx', index=False)
    print("✅ Created: test_files/target_table_data.xlsx")
    
    # Create another sample file with different structure
    sample_data2 = {
        'Product Code': ['P001', 'P002', 'P003'],
        'Product Name': ['Product A', 'Product B', 'Product C'],
        'Commission Rate': [0.05, 0.03, 0.07],
        'Min Amount': [1000, 2000, 1500]
    }
    
    df2 = pd.DataFrame(sample_data2)
    df2.to_csv('test_files/product_commission.csv', index=False)
    print("✅ Created: test_files/product_commission.csv")
    
    print("\n📁 Sample files created in 'test_files' directory")
    print("📋 You can now test the file upload functionality with these files")

if __name__ == "__main__":
    try:
        create_sample_files()
    except ImportError:
        print("❌ pandas is required to create sample files")
        print("💡 Install with: pip install pandas openpyxl")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating sample files: {e}")
        sys.exit(1)
