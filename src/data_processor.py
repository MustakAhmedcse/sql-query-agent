"""
Data Processor - আপনার SRF-SQL pairs process করার জন্য
Simple এবং easy to understand
"""
import json
import os
import pandas as pd
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """SRF-SQL data process করার জন্য simple class"""
    
    def __init__(self, data_path="./data/training_data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
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
        Data clean করে processed format এ convert করি
        """
        processed_data = []
        
        for item in data:
            try:
                # Basic cleaning
                srf_text = self._clean_text(item.get('srf', ''))
                sql_query = self._clean_sql(item.get('sql', ''))
                supporting_table = item.get('supporting_table', '')
                
                # Skip empty data
                if not srf_text or not sql_query:
                    continue
                
                processed_item = {
                    'id': len(processed_data) + 1,
                    'srf_text': srf_text,
                    'sql_query': sql_query,
                    'supporting_table': supporting_table,
                    'srf_length': len(srf_text),
                    'sql_length': len(sql_query)
                }
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.warning(f"Error processing item: {str(e)}")
                continue
        
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
    your_jsonl_file = "../MyBL_FEB_MAR_APR_MAY_25/srf_sql_pairs.jsonl"
    
    # Process করি
    result = process_your_data(your_jsonl_file)
    
    if result:
        print(f"\n🎉 Successfully processed {len(result)} SRF-SQL pairs!")
    else:
        print("\n😔 Data processing failed!")
