"""
Data Processor - আপনার SRF-SQL pairs process করার জন্য
Simple এবং easy to understand
Enhanced with metadata extraction
"""
import json
import os
from typing import Dict, List, Optional
import pandas as pd
import re
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """SRF-SQL data process করার জন্য simple class"""
    
    def __init__(self, data_path="./data/training_data",mapping_file="./commission_mapping.json"):
        self.MAPPING = self.load_mapping(mapping_file)
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
    def load_mapping(self, path: str) -> List[Dict[str, str]]:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    def load_existing_data(self, jsonl_file_path):
        """
        আপনার existing srf_sql_pairs.jsonl file load করে
        """
        try:
            data = []
            logger.info(f"Loading data from: {jsonl_file_path}")
            
            with open(jsonl_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():  # Empty line skip করি
                        item = json.loads(line)
                        data.append(item)
            
            logger.info(f"Loaded {len(data)} SRF-SQL pairs")
            return data            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return []
    
    def clean_and_process_data(self, data):
        """
        Data clean করে processed format এ convert করি এবং মেটাডাটা এক্সট্র্যাক্ট করি
        """
        processed_data = []
        
        for item in data:
            try:
                # Basic cleaning
                srf_text = self._clean_text(item.get('srf', ''))
                sql_query = self._clean_sql(item.get('sql', ''))
                
                # Skip empty data
                if not srf_text or not sql_query:
                    continue
                
                # মেটাডাটা এক্সট্র্যাক্ট করি
                metadata = self.extract_commission_metadata(srf_text)
                
                processed_item = {
                    'id': len(processed_data) + 1,
                    'srf_text': srf_text,
                    'sql_query': sql_query,
                    'srf_length': len(srf_text),
                    'sql_length': len(sql_query),
                    'commission_name': metadata['commission_name'],
                    'commission_type': metadata['commission_type']
                }
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.warning(f"Error processing item: {str(e)}")
                continue
        
        # Categorize data
        processed_data = self.categorize_data_by_metadata(processed_data)
        
        logger.info(f"Processed {len(processed_data)} valid items")
        return processed_data
    
    def _clean_text(self, text):
        """Text clean করার simple function"""
        if not text:
            return ""
        
        # Basic cleaning
        text = str(text).strip()
        # Remove extra spaces
        text = ' '.join(text.split())
        # Remove special characters that might cause issues
        text = text.replace('\x00', '').replace('\r', '\n')
        
        return text
    
    def _clean_sql(self, sql):
        """SQL clean করার function"""
        if not sql:
            return ""
        
        sql = str(sql).strip()
        # Basic SQL formatting
        sql = sql.replace('\r\n', '\n').replace('\r', '\n')
        
        return sql
    
    def save_processed_data(self, processed_data, filename="processed_training_data.json"):
        """Processed data save করি"""
        try:
            output_path = self.data_path / filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved processed data to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            return None
    
    def get_data_statistics(self, data):
        """Data এর basic statistics"""
        if not data:
            return {}
        
        stats = {
            'total_items': len(data),
            'avg_srf_length': sum(item['srf_length'] for item in data) / len(data),
            'avg_sql_length': sum(item['sql_length'] for item in data) / len(data),
            'min_srf_length': min(item['srf_length'] for item in data),
            'max_srf_length': max(item['srf_length'] for item in data)
        }
        
        return stats
    
    def extract_commission_metadata(self, srf_text):
        """
        SRF থেকে কমিশন টাইপ এবং নাম এক্সট্র্যাক্ট করে
        """
        commission_name = None
        commission_type = None
        
        try:
            # Enhanced রিপোর্ট টাইটেল এক্সট্র্যাক্ট করি
            # Multiple patterns try করি
            report_title_patterns = [
                r"Report Title:\s*([^\u0007\r\n]+?)(?:\s*\u0007|\s*Report Description|$)",  # Unicode aware
                r"Report Title:\s*(.+?)(?:\s*\u0007)",  # Specifically for \u0007
                r"Report Title:\s*(.+?)(?:\r|\n|$)",    # Original pattern
                r"Report Title:\s*([^\\]+?)(?:\s*\\)",  # For escaped characters
                r"Report Title:\s*(.+?)(?=\s+Report Description|\s+\u0007|$)"  # Lookahead pattern
            ]
            
            commission_name = None
            for pattern in report_title_patterns:
                report_title_match = re.search(pattern, srf_text, re.IGNORECASE | re.DOTALL)
                if report_title_match:
                    commission_name = report_title_match.group(1).strip()
                    # Clean up any remaining special characters
                    commission_name = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', commission_name)
                    commission_name = commission_name.strip()
                    
                    if commission_name:  # Valid name found
                        break
            
            if commission_name:
                metadata_by_title = self.extract_commission_metadata_from_title(commission_name)
                # উন্নত ফাংশন ব্যবহার করে কমিশন টাইপ এক্সট্র্যাক্ট করি
                #commission_type = self._extract_commission_type(commission_name)
                commission_type = metadata_by_title['type'] if metadata_by_title else "unknown"
                
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
        
        return {
            "commission_name": commission_name or "unknown",
            "commission_type": commission_type or "unknown"
        }

    
    def extract_commission_metadata_from_title(self, text: str) -> Optional[Dict[str, str]]:
        text_lower = text.lower()
        best_match = None
        max_keywords = 0

        for entry in self.MAPPING:
            keywords = entry["keywords"]
            if all(kw.lower() in text_lower for kw in keywords):
                if len(keywords) > max_keywords:
                    best_match = entry
                    max_keywords = len(keywords)

        return best_match
    def categorize_data_by_metadata(self, processed_data):
        """
        Add categories to data for better filtering
        """
        for item in processed_data:
            srf_text = item['srf_text'].lower()
            
            # Categorize by commission type
            if 'hourly' in srf_text:
                item['sub_category'] = 'hourly'
            elif 'special day' in srf_text:
                item['sub_category'] = 'special_day'
            elif 'regular' in srf_text:
                item['sub_category'] = 'regular'
            else:
                item['sub_category'] = 'other'
                
        
        return processed_data
# Usage example function
def process_your_data(jsonl_file_path):
    """
    আপনার data process করার জন্য main function
    """
    print("🚀 Starting data processing...")
    
    # Data processor তৈরি করি
    processor = DataProcessor()
    
    # আপনার existing data load করি
    raw_data = processor.load_existing_data(jsonl_file_path)
    
    if not raw_data:
        print("❌ No data found to process")
        return None
    
    # Data clean ও process করি
    processed_data = processor.clean_and_process_data(raw_data)
    
    # Statistics দেখি
    stats = processor.get_data_statistics(processed_data)
    print("\n📊 Data Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Processed data save করি
    saved_path = processor.save_processed_data(processed_data)
    
    if saved_path:
        print(f"✅ Data processing completed! Saved to: {saved_path}")
        return processed_data
    else:
        print("❌ Failed to save processed data")
        return None

# Direct run করার জন্য
if __name__ == "__main__":
    # আপনার existing data file path
    your_jsonl_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "srf_sql_pairs.jsonl")
    
    # Process করি
    result = process_your_data(your_jsonl_file)
    
    if result:
        print(f"\n🎉 Successfully processed {len(result)} SRF-SQL pairs!")
    else:
        print("\n😔 Data processing failed!")
